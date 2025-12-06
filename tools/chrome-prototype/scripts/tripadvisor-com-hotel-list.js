console.log( 'Loaded tripadvisor.com hotel list content script.' );


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
   
    const cardNodeList = document.querySelectorAll( '.listItem' );
    cardNodeList.forEach( cardNode => {
	addButtonToSearchListCard( cardNode );
    });

    
}


function addButtonToSearchListCard( cardNode ) {

    const vtButtonNode = cardNode.querySelector( '.' + VT_BUTTON_CLASS );
    if ( vtButtonNode ) {
	return;
    }
    addButtonToNode( cardNode,
		     cardNode,
		     'h3',
		     LocationCategory.LODGING,
		     null,
		     199 );
}

/*
.listItem

data-automation="hotel-card-title"

h3

*/
