console.log( 'Loaded google.com hotel list content script.' );


addButtonsIfNeeded();


// Something reshuffles the items on the page and the bnuttons get removed,
// so we want to refresh the buttons if we detect changes.
//
const observer = new MutationObserver(mutations => {
    // logMutations();    
    addButtonsIfNeeded();
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});


function addButtonsIfNeeded() {
   
    const titleNodeListH1 = document.querySelectorAll( 'h1' );
    titleNodeListH1.forEach( titleNode => {
	const cardNode = titleNode.parentNode;
	addButtonToSearchListCard( cardNode, 'h1' );
    });
}


function addButtonToSearchListCard( cardNode, titleSelector ) {

    const vtButtonNode = cardNode.querySelector( '.' + VT_BUTTON_CLASS );
    if ( vtButtonNode ) {
	return;
    }
    addButtonToNode( cardNode,
		     cardNode,
		     titleSelector,
		     LocationCategory.LODGING,
		     null );
}
