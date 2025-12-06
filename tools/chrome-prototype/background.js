const VT_GMM_HOME_URL = 'https://www.google.com/maps/d';

chrome.runtime.onInstalled.addListener(() => {

    // TODO: Use constants for URL
    chrome.tabs.create({ url: VT_GMM_HOME_URL });
});


let vtContextMenuInstalled = false;

if ( ! vtContextMenuInstalled ) {

    chrome.contextMenus.create({
	id: 'vtContextMenu',
	title: "Search on Vacation Map",
	contexts: [ "selection" ]
    });
    chrome.contextMenus.onClicked.addListener(function(info, tab) {
	const selectedText = info.selectionText;
	console.log("VT[Context] Selected text: " + selectedText);
	sendSelectedTextToMyMap( selectedText );
     });
    vtContextMenuInstalled = true;
}



// This relays messages from content scripts to the the mymaps.js script.
//
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log( "VT[background] receiving message: " + request.text );
    if ( ! request.text ) {
	return;
    }
    sendSelectedTextToMyMap( request.text, request.category );
});


function sendSelectedTextToMyMap( selectedText, category = null ) {

    chrome.storage.local.get( { mapInfoList: [] }, function(result) {
	let mapInfoList = result.mapInfoList;
	if ( mapInfoList.length < 1 ) {
	    chrome.tabs.create({ url: VT_GMM_HOME_URL });
	    return;
	}
	let mapInfo = mapInfoList[0];
	console.log( "VT[background] sending message: " + selectedText );
	chrome.tabs.sendMessage( mapInfo.tabId, { text: selectedText,
						  category: category } );
	switchToMapsTab( mapInfo );
	
    });
}


function switchToMapsTab( mapInfo ) {

    // REFACTOR: Dupe in popup.js
    
    chrome.tabs.query( {}, function(tabs) {
	let existingTab = tabs.find( tab => tab.id === mapInfo.tabId );
	if ( existingTab ) {
	    chrome.tabs.update(mapInfo.tabId, {active: true});
	} else {
	    chrome.tabs.create( {url: mapInfo.url} );
	}
    });
}

