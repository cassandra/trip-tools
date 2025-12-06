function addButtonToNode( positionNode,
			  selectorNode,
			  titleNodeSelector,
			  category = null,
			  buttonId = null,
			  zIndex = 999,
			  eventName = 'click' ) {

    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.top = "0";
    container.style.left = "0";
    container.style.zIndex = zIndex;

    const button = createAddButton( buttonId );

    container.appendChild( button );
    positionNode.style.position = "relative";
    positionNode.insertBefore( container, positionNode.firstChild );


    button.addEventListener( eventName, function(event) {
	event.stopImmediatePropagation();

	console.log( 'VT Button clicked on:' );
	console.log( container );
	
	const titleNode = selectorNode.querySelector( titleNodeSelector );
	const title = titleNode.textContent;
	console.log( 'VT sending title = ' + title
		     + ', category = ' + category );
	console.log( titleNode );

	const pageUrl = window.location.href;
	
	// TODO: Use shared namespace for categories
	chrome.runtime.sendMessage({ text: title,
				     category: category,
				     pageUrl: pageUrl });

    });
}


function createButtonAtLocation( x, y,
				 title,
				 category = null,
				 buttonId = null,
				 durationMs = null,
				 zIndex = 999 ) {
    let button = createAddButton( buttonId );
    button.style.position = 'absolute';

    button.style.left = (window.scrollX + x) + 'px';
    button.style.top = (window.scrollY + y) + 'px';
    button.style.zIndex = zIndex;
    button.onclick = function() {
	console.log( 'VT Button clicked on:' );
        window.getSelection().removeAllRanges();
	button.remove();
	console.log( 'VT sending title = ' + title
		     + ', category = ' + category );
	chrome.runtime.sendMessage({ text: title,
				     category: category });
    };

    if ( durationMs ) {
	setTimeout(() => {
	    button.remove(); // Remove the button after timeout
	}, durationMs );
    }
    
    document.body.appendChild(button);
}


function createAddButton( buttonId ) {

    const button = document.createElement("button");
    button.id = buttonId;
    button.innerText = "Add";
    button.classList.add( VT_BUTTON_CLASS );
    button.classList.add( 'external' );
    return button;
}


// ============================================================
// Debugging Helpers


function logMutations( mutations ) {
    console.log( 'Mutation count = ' + mutations.length );
    mutations.forEach(mutation => {
	console.log( 'Mutation type = ' + mutation.type );
	if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
	    for ( let i = 0; i < mutation.addedNodes.length; i++) {
		let node = mutation.addedNodes[i];
		console.log( node );
		if ( node.classList ) {
		    let isMapHoverCard = false;
		    for ( let ci = 0; ci < node.classList.length; ci++ ) {
			let className = node.classList[ci];
			console.log( 'Class = ' + className );
		    }
		}
	    }
	}
    });
}

