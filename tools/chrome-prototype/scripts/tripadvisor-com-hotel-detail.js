console.log( 'Loaded tripadvisor.com hotel detail content script.' );

decoratePageIfNeeded();

// Something reshuffles the items on the page and the bnuttons get removed,
// so we want to refresh the buttons if we detect changes.
//
const observer = new MutationObserver(mutations => {
    // logMutations();    
    decoratePageIfNeeded();
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});


function decoratePageIfNeeded() {
    let titleNode = document.getElementById( 'HEADING' );
    let titleContainer = titleNode.parentNode.parentNode.parentNode;
    const titleButtonId = 'vt-title-button';

    const vtButtonNode = document.getElementById( titleButtonId );
    if ( vtButtonNode ) {
	return;
    }

    addButtonToNode( titleContainer,
		     titleContainer,
		     '#HEADING',
		     titleButtonId,
		     LocationCategory.LODGING );
}

