// From Google's custom map urls
const MY_MAPS_URL_DOMAIN_NAME = 'www.google.com';
const MY_MAPS_URL_HOME_PATH = '/maps/d';
const MY_MAPS_URL_EDIT_PATH = '/maps/d/edit';
const MY_MAPS_URL_MAP_ID_PARAM_NAME = 'mid';

// From popup.html
const ADD_MAP_BUTTON_TAG_ID = 'vtAddMapButton';
const MAKE_CURRENT_MAP_BUTTON_TAG_ID = 'vtMakeCurrentMapButton';
const CURRENT_MAP_CONTAINER_ID = 'vt-current-map-container';
const CURRENT_MAP_LIST_TAG_ID = 'vtMapListCurrent';
const OTHER_MAPS_CONTAINER_ID = 'vt-other-maps-container';
const OTHER_MAP_LIST_TAG_ID = 'vtMapListOther';
const MY_MAPS_HOME_TAG_ID = 'vtMyMapsHomeButton';
const MAPS_LIST_REFRESH_TAG_ID = 'vtRefreshMapsList';
const VT_TOGGLE_SELECT_DECORATE_ID = 'vtToggleSelectDecorate';
const VT_SELECT_DECORATE_VALUE_ID = 'vtSelectDecorateValue';
const VT_KILL_STICKY_BUTTON_TAG_ID = 'vtKillSticky';


// ============================================================
// Popup Initializations


let currentTabInfo = {};  // Gets set on load


chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {

    currentTabInfo = tabInfoFromTab( tabs[0] );

    chrome.storage.local.get( { mapInfoList: [], selectDecorateEnabled: true }, function(result) {
	let mapInfoList = result.mapInfoList;
	initializeForMyMapsPage( currentTabInfo, mapInfoList );
	displayMapsList( mapInfoList );

	const selectDecorate = document.getElementById( VT_SELECT_DECORATE_VALUE_ID );
        if ( result.selectDecorateEnabled ) {
            selectDecorate.textContent = 'ON';
        } else {
            selectDecorate.textContent = 'OFF';
        }
    });

});


function initializeForMyMapsPage( tabInfo, mapInfoList ) {

    let mapId = getMapIdFromUrl( tabInfo.url );
    if ( mapId == null ) {
	return;
    }
    console.log( 'On map page, mapId = ' + mapId );
    if ( ! mapInfoList || ! isMapIdInMapsList( mapId, mapInfoList ) ) {
	document.getElementById( ADD_MAP_BUTTON_TAG_ID ).style.display = 'block';
    } else if ( mapId != mapInfoList[0].mapId ) {
	document.getElementById( MAKE_CURRENT_MAP_BUTTON_TAG_ID ).style.display = 'block';
    }


}


document.getElementById( ADD_MAP_BUTTON_TAG_ID ).addEventListener('click', function() {
    addMapPage();
});


document.getElementById( MAKE_CURRENT_MAP_BUTTON_TAG_ID ).addEventListener('click', function() {
    makeCurrentMapPage();
});


document.getElementById( MY_MAPS_HOME_TAG_ID ).addEventListener('click', function() {
    visitMyMapsHome();
});


document.getElementById( MAPS_LIST_REFRESH_TAG_ID ).addEventListener('click', function() {
    refreshMapInfoListFromTabs();
});

document.getElementById( VT_KILL_STICKY_BUTTON_TAG_ID ).addEventListener('click', function() {
    vtKillSticky();
});


document.getElementById( VT_TOGGLE_SELECT_DECORATE_ID ).addEventListener('click', function() {
    chrome.storage.local.get( { selectDecorateEnabled: true }, function(result) {
	chrome.storage.local.set({ selectDecorateEnabled: ! result.selectDecorateEnabled }, function() {
	    window.location.reload();
	} );
    });
});

// ============================================================
// Button Actions


function addMapPage( ) {

    let mapId = getMapIdFromUrl( currentTabInfo.url );
    if ( mapId == null ) {
	return;
    }
    console.log( 'Adding map page, mapId = ' + mapId );

    chrome.storage.local.get({mapInfoList: []}, function(result) {
	let mapInfoList = result.mapInfoList;
	if ( isMapIdInMapsList( mapId, mapInfoList ) ) {
	    console.log( 'Map page already in list, mapId = ' + mapId );
	    return;
	}


	let mapInfo = mapInfoFromIdAndTabInfo( mapId, currentTabInfo );
	mapInfoList.unshift( mapInfo );

	chrome.storage.local.set({mapInfoList: mapInfoList}, function() {
	    console.log('Map list updated.');
	    window.location.reload();
	});

    });
}


function makeCurrentMapPage( ) {
    let mapId = getMapIdFromUrl( currentTabInfo.url );
    if ( mapId == null ) {
	return;
    }
    console.log( 'Making current map current, mapId = ' + mapId );

    chrome.storage.local.get({mapInfoList: []}, function(result) {
	let mapInfoList = result.mapInfoList;
	if ( mapInfoList.length < 1 ) {
	    addMapPage();
	    return;
	}
	if ( mapInfoList[0].mapId == mapId ) {
	    return;
	}
	let newMapInfoList = [];
	let currentPageMapInfo = null;

	for ( let mi = 0; mi < mapInfoList.length; mi++ ) {
	    let mapInfo = mapInfoList[mi];
	    if ( mapInfo.mapId == mapId ) {
		currentPageMapInfo = mapInfo;
	    } else {
		newMapInfoList.push( mapInfo );
	    }
	}
	if ( ! currentPageMapInfo ) {
	    console.log( 'Did not find current map page in list' );
	    return;
	}
	newMapInfoList.unshift( currentPageMapInfo );

	chrome.storage.local.set({ mapInfoList: newMapInfoList }, function() {
	    console.log('Map list updated.');
	    window.location.reload();
	});

    });

}


function visitMyMapsHome( ) {
    let myMapsHomeUrl = 'https://' + MY_MAPS_URL_DOMAIN_NAME + MY_MAPS_URL_HOME_PATH;
    chrome.tabs.create( { url: myMapsHomeUrl } );
}


function refreshMapInfoListFromTabs() {
    console.log( 'VT Refreshing maps list from tabs' );
    var updatedMapInfoMap = {};
    chrome.tabs.query( {}, function(tabs) {
	tabs.forEach( tab => {

	    let mapId = getMapIdFromUrl( tab.url );
	    if ( mapId == null ) {
		return;
	    }
	    console.log( 'VT Found map in tab: ' + mapId );

	    let mapInfo = {
		url: tab.url,
		tabId: tab.id,
		mapId: mapId,
		label: getMapsLabelFromPageTitle( tab.title )
	    };

	    updatedMapInfoMap[mapId] = mapInfo;

	});
    });

    chrome.storage.local.get( { mapInfoList: [] }, function(result) {
	let mapInfoList = result.mapInfoList;
	var newMapInfoList = [];
	mapInfoList.forEach( mapInfo => {
	    if ( ! mapInfo ) {
		return;
	    }
	    if ( mapInfo.mapId in updatedMapInfoMap ) {
		newMapInfoList.push( updatedMapInfoMap[mapInfo.mapId] );
	    } else {
		newMapInfoList.push( mapInfo );
	    }
	});

	chrome.storage.local.set( { mapInfoList: newMapInfoList }, function() {
	    window.location.reload();
	});


    });
}


// ============================================================
// Models


function tabInfoFromTab( tab ) {
    return {
	url: tab.url,
	tabId: tab.id,
	title: tab.title
    };
}


function mapInfoFromIdAndTabInfo( mapId, tabInfo ) {
    return {
	mapId: mapId,
	tabId: tabInfo.tabId,
	url: tabInfo.url,
	label: getMapsLabelFromPageTitle( tabInfo.title )
    };
}


// ============================================================
// Map List Management


function displayMapsList(mapInfoList) {

    const currentContainer = document.getElementById( CURRENT_MAP_LIST_TAG_ID );
    currentContainer.innerHTML = '';

    const otherContainer = document.getElementById( OTHER_MAP_LIST_TAG_ID );
    otherContainer.innerHTML = '';

    let seenCurrent = false;
    let seenOthers = false;
    mapInfoList.forEach(mapInfo => {
	if ( ! mapInfo ) {
	    return;
	}
	let listItem = createMapsListItem( mapInfo );
	if ( seenCurrent ) {
	    otherContainer.appendChild(listItem);
	    seenOthers = true;
	} else {
	    currentContainer.appendChild(listItem);
	    seenCurrent = true;
	}
    });

    if ( ! seenOthers ) {
	document.getElementById( OTHER_MAPS_CONTAINER_ID ).remove();
    }
    if ( ! seenCurrent ) {
	let container = document.getElementById( CURRENT_MAP_CONTAINER_ID );
	container.innerHTML = '';
	let label = document.createElement('h3');
	label.textContent = 'No maps added.';
	container.appendChild( label );
    }
}


function createMapsListItem( mapInfo ) {

    let listItem = document.createElement('div');
    listItem.className = 'vt-map-list-item';

    let labelItem = document.createElement('a');
    labelItem.href = mapInfo.url;
    labelItem.setAttribute( 'target', '_blank' );
    labelItem.textContent = mapInfo.label || mapInfo.url || mapInfo;
    labelItem.style.cursor = 'pointer';
    labelItem.addEventListener('click', function(e) {
	e.preventDefault();
	switchToMapTab(mapInfo);
    });


    let removeItem = document.createElement('button');
    removeItem.className = 'vt-btn remove';
    removeItem.textContent = 'X';
    removeItem.addEventListener('click', function(e) {
	e.preventDefault();
	removeMapsListItem( mapInfo );
    });


    listItem.appendChild( labelItem );
    listItem.appendChild( removeItem );
    return listItem;
}



function removeMapsListItem( toRemoveMapInfo ) {

    let newMapInfoList = [];

    chrome.storage.local.get( { mapInfoList: [] }, function(result) {
	let mapInfoList = result.mapInfoList;

	let newMapInfoList = mapInfoList.filter( mapInfo => toRemoveMapInfo.mapId !== mapInfo.mapId );

	chrome.storage.local.set( { mapInfoList: newMapInfoList }, function() {
	    window.location.reload();
	});
    });

}


// ============================================================
// Helpers


function isGoogleMapsPage( url ) {
    if ( url == null ) {
	return false;
    }
    return url.includes( MY_MAPS_URL_DOMAIN_NAME + MY_MAPS_URL_EDIT_PATH );
}


function getMapIdFromUrl( url ) {
    if ( ! isGoogleMapsPage( url ) ) {
	return null;
    }
    let urlObj = new URL( url );
    let params = urlObj.searchParams;
    return params.get( MY_MAPS_URL_MAP_ID_PARAM_NAME );
}


function getMapUrlFromId(mapId) {
    return 'https://' + MY_MAPS_URL_DOMAIN_NAME + MY_MAPS_URL_EDIT_PATH + '?' + MY_MAPS_URL_MAP_ID_PARAM_NAME + '=' + mapId;
}


function isMapIdInMapsList( mapId, mapInfoList ) {
    return mapInfoList.some( mapInfo => mapId === mapInfo.mapId );
}


function getMapsLabelFromPageTitle( pageTitle ) {
    if ( pageTitle.endsWith( " - Google My Maps" )) {
	return pageTitle.replace( " - Google My Maps", "" );
    }
    return pageTitle;
}


function switchToMapTab(mapInfo) {

    chrome.tabs.query( {}, function(tabs) {
	let existingTab = tabs.find( tab => tab.id === mapInfo.tabId );
	if ( existingTab ) {
	    chrome.tabs.update(mapInfo.tabId, {active: true});
	} else {
	    chrome.tabs.create( {url: mapInfo.url} );
	}
    });
}


// ============================================================
// Kill Sticky
//
// Source: https://github.com/eemeli/kill-sticky/tree/main
// Released as open source under the MIT license.

const vtKillSticky = () => {
  function killSticky(root, ksCount) {
    const iter = document.createNodeIterator(root, NodeFilter.SHOW_ELEMENT);
    let node;
    while ((node = iter.nextNode())) {
      const { display, position } = window.getComputedStyle(node);
      if (
        (position === "fixed" || position === "sticky") &&
        display !== "none" &&
        node.tagName !== "BODY"
      ) {
        node.parentNode.removeChild(node);
      } else if (ksCount > 0) {
        const shadowRoot = node.openOrClosedShadowRoot;
        if (shadowRoot) killSticky(shadowRoot, ksCount - 1);
      }
    }
  }
  const ksCount = Number(document.body.dataset["ks"] ?? 0);
  killSticky(document.body, ksCount);
  const fix = "; overflow: visible !important; position: relative !important";
  document.body.style.cssText += fix;
  document.documentElement.style.cssText += fix;
  document.body.dataset["ks"] = ksCount + 1;
};
