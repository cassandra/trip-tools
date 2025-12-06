console.log( 'Loaded booking.com detail content script.' );

decoratePageIfNeeded();


function decoratePageIfNeeded() {
    let titleContainer = document.getElementById( 'wrap-hotelpage-top' );

    const titleButtonId = 'vt-title-button';

    const vtButtonNode = document.getElementById( titleButtonId );
    if ( vtButtonNode ) {
	return;
    }

    addButtonToNode( titleContainer,
		     document.body,
		     '#hp_hotel_name h2',
		     titleButtonId,
		     LocationCategory.LODGING );
}

