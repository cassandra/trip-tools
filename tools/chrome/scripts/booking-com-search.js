console.log( 'Loaded booking.com search content script.' );


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
   
    const cardNodeList = document.querySelectorAll( 'div[data-testid="property-card"]' );
    cardNodeList.forEach( cardNode => {
	addButtonToSearchListCard( cardNode );
    });

    const mapCardLinkNodes = document.querySelectorAll( '[data-testid="property-list-map-card"]' );
    mapCardLinkNodes.forEach( linkNode => {
	const liNode = linkNode.parentNode;
	addButtonToMapListCard( liNode );
    });

    const mapCardHoverNodes = document.querySelectorAll( '.map-card__content-container' );
    mapCardHoverNodes.forEach( hoverNode => {
	addButtonToMapHoverCard( hoverNode );
    });
    
}    


function addButtonToSearchListCard( cardNode ) {

    const vtButtonNode = cardNode.querySelector( '.' + VT_BUTTON_CLASS );
    if ( vtButtonNode ) {
	return;
    }
    addButtonToNode( cardNode,
		     cardNode,
		     'div[data-testid="title"]',
		     LocationCategory.LODGING,
		     null,
		     199 );
}


function addButtonToMapListCard( mapCardNode ) {

    const vtButtonNode = mapCardNode.querySelector( '.' + VT_BUTTON_CLASS );
    if ( vtButtonNode ) {
	return;
    }
    addButtonToNode( mapCardNode,
		     mapCardNode,
		     'h2[data-testid="header-title"]',
		     LocationCategory.LODGING );
}

function addButtonToMapHoverCard( mapCardNode ) {

    const vtButtonNode = mapCardNode.querySelector( '.' + VT_BUTTON_CLASS );
    if ( vtButtonNode ) {
	return;
    }
    addButtonToNode( mapCardNode,
		     mapCardNode,
		     '.map-card__title-link',
		     LocationCategory.LODGING,
		     null,
		     9999,
		     'mousedown' );
}
