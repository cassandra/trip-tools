const VT_BUTTON_DECORATION_LIFETIME_MS = 5000;

let isSelectDecorateEnabled = true;

chrome.storage.local.get( { selectDecorateEnabled: true }, function(result) {
    isSelectDecorateEnabled = result.selectDecorateEnabled;
});

// Make sure we can be reactive to changes made by popup.js
chrome.storage.onChanged.addListener(function(changes, namespace) {
  for (let [key, { oldValue, newValue }] of Object.entries(changes)) {
    if ( key === 'selectDecorateEnabled' ) {
      isSelectDecorateEnabled = newValue;
    }
  }
});


const currentURL = window.location.href;
console.log( 'Loaded general page content script: ' + currentURL );

const ignorePage = (
    false
    || currentURL.startsWith( 'https://www.google.com/maps/d/edit' )
);


let previousSelection = '';

if ( ! ignorePage ) {

    document.addEventListener('mousedown', function() {
	previousSelection = window.getSelection().toString();
    });


    document.addEventListener('mouseup', function(e) {
	if ( ! isSelectDecorateEnabled ) {
	    return;
	}
	let currentSelection = window.getSelection().toString();
	if ( previousSelection !== currentSelection && currentSelection !== '') {
	    createButtonAtLocation( e.clientX,
				    e.clientY,
				    currentSelection,
				    LocationCategory.ATTRACTIONS,
				    null,
				    VT_BUTTON_DECORATION_LIFETIME_MS );
	}
    });

}
