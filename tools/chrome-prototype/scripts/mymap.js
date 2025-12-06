// ============================================================
// Initializations


chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // Accepting selected text from content pages.
    
    if (request.text) {
	let inputField = document.getElementById('mapsprosearch-field');
	if (inputField) {
	    inputField.value = request.text;
	    
	    let submitButton = document.querySelector('#mapsprosearch-button div');
	    
	    if (submitButton) {
		submitButton.click();


		
		if ( request.category ) {
		    const buttonId = addToMapButtonId( request.category );
		    waitForElement( '#' + buttonId ).then( () => {
			const dialogElement = document.querySelector( 'div[role="dialog"]' );
			handleAddToLocationButtonClick( dialogElement,
							request.category );
			
		    });
		}


		
		
	    }
	}
    }
});


// Mutation observer to watch for changes in the DOM
const observer = new MutationObserver(mutations => {

    console.log( 'Adding DOM mutation observer' );
    
    mutations.forEach(mutation => {
	if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
	    
	    for ( let i = 0; i < mutation.addedNodes.length; i++) {
		let node = mutation.addedNodes[i];

                if (node.matches && node.matches("div[role='dialog']")) {

		    console.log( 'Dialog DOM mutation observed' );

		    let addToMapButton = node.querySelector( '#' + GMM_ADD_TO_MAP_BUTTON_ID );
		    if ( addToMapButton ) {
			decorateAddToMapDialog( node );
			continue;
		    }
		    let infoContainer = node.querySelector( '#' + GMM_INFO_CONTAINER_ID );
		    if ( infoContainer ) {
			decorateLocationDetailsDialog( node );
			continue;
		    }
		}
	    }
        }
    });    
});


observer.observe(document.body, {
    childList: true,
    subtree: true
});


// ============================================================
// Custom Location Attributes


const DesirabilityStatus = {
    MAYBE: 'maybe',
    MUST_DO: 'must_do',
    IF_TIME: 'if_time'
};


const DesirabilityStatusDef = {
    [DesirabilityStatus.MAYBE]: { label: 'Maybe' },
    [DesirabilityStatus.MUST_DO]: { label: 'Must Do' },
    [DesirabilityStatus.IF_TIME]: { label: 'If Time' }
};    


const BookingStatus = {
    NONE: 'none',
    NEEDED: 'needed',
    BOOKED: 'booked'
};


const BookingStatusDef = {
    [BookingStatus.NONE]: { label: 'None' },
    [BookingStatus.NEEDED]: { label: 'Needed' },
    [BookingStatus.BOOKED]: { label: 'Booked' }
};    


const PriceRange = {
    LOW: 'low',
    MODERATE: 'moderate',
    HIGH: 'high'
};


const PriceRangeDef = {
    [PriceRange.LOW]: { label: 'Low' },
    [PriceRange.MODERATE]: { label: 'Moderate' },
    [PriceRange.HIGH]: { label: 'High' }
};    


const Rating = {
    FAIR: 'low',
    GOOD: 'moderate',
    EXCELLENT: 'high'
};


const RatingDef = {
    [Rating.FAIR]: { label: 'Fair' },
    [Rating.GOOD]: { label: 'Good' },
    [Rating.EXCELLENT]: { label: 'Excellent' }
};    


const PaymentStatus = {
    NONE: 'none',
    PARTIAL: 'partial',
    PAID: 'paid'
};


const PaymentStatusDef = {
    [PaymentStatus.NONE]: { label: 'None' },
    [PaymentStatus.PARTIAL]: { label: 'Partial' },
    [PaymentStatus.PAID]: { label: 'Paid' }
};    



const CustomAttributeType = {
    LINK_LIST: 'link-list',
    DROP_DOWN: 'drop-down',
    TEXT_AREA: 'text-area'
};


const CustomAttribute = {
    EXTERNAL_LINKS: 'externalLinks',
    DESIRABILITY_STATUS: 'desirabilityStatus',
    BOOKING_STATUS: 'bookingStatus',
    PRICE_RANGE: 'priceRange',
    RATING: 'rating',
    PAYMENT_STATUS: 'paymentStatus',
    LOCATION_FEATURES: 'locationFeatures',
    PAYMENT_DETAILS: 'paymentDetails',
    CANCELLATION_POLICY: 'cancellationPolicy'
};


const CustomAttributeDef = {
    [CustomAttribute.EXTERNAL_LINKS]: {
	name: CustomAttribute.EXTERNAL_LINKS,
	type: CustomAttributeType.LINK_LIST,
	label: 'External Links'
    },
    [CustomAttribute.DESIRABILITY_STATUS]: {
	name: CustomAttribute.DESIRABILITY_STATUS,
	type: CustomAttributeType.DROP_DOWN,
	valuesDef: DesirabilityStatusDef,
	label: 'Desirability'
    },
    [CustomAttribute.BOOKING_STATUS]: {
	name: CustomAttribute.BOOKING_STATUS,
	type: CustomAttributeType.DROP_DOWN,
	valuesDef: BookingStatusDef,
	label: 'Booking Status'
    },
    [CustomAttribute.PRICE_RANGE]: {
	name: CustomAttribute.PRICE_RANGE,
	type: CustomAttributeType.DROP_DOWN,
	valuesDef: PriceRangeDef,
	label: 'Price Range'
    },
    [CustomAttribute.RATING]: {
	name: CustomAttribute.RATING,
	type: CustomAttributeType.DROP_DOWN,
	valuesDef: RatingDef,
	label: 'Rating'
    },
    [CustomAttribute.PAYMENT_STATUS]: {
	name: CustomAttribute.PAYMENT_STATUS,
	type: CustomAttributeType.DROP_DOWN,
	valuesDef: PaymentStatusDef,
	label: 'Payment Status'
    },
    [CustomAttribute.LOCATION_FEATURES]: {
	name: CustomAttribute.LOCATION_FEATURES,
	type: CustomAttributeType.TEXT_AREA,
	label: 'Features'
    },
    [CustomAttribute.PAYMENT_DETAILS]: {
	name: CustomAttribute.PAYMENT_DETAILS,
	type: CustomAttributeType.TEXT_AREA,
	label: 'Payment Details'
    },
    [CustomAttribute.CANCELLATION_POLICY]: {
	name: CustomAttribute.CANCELLATION_POLICY,
	type: CustomAttributeType.TEXT_AREA,
	label: 'Cancellation Policy'
    }
};



// ============================================================
// Location Category Definitions


const GMM_ATTRACTION_ATTR_RGB_VALUE = 'RGB (245, 124, 0)';


const LocationCategoryDef = {
    [LocationCategory.ATTRACTIONS]: {
	type: LocationCategory.ATTRACTIONS,
	colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	iconCodeValue: '1535',
	customAttributeList: [
	    CustomAttribute.EXTERNAL_LINKS,
	    CustomAttribute.DESIRABILITY_STATUS,
	    CustomAttribute.RATING,
	    CustomAttribute.PRICE_RANGE
	],
	subcategoryList: [
	    { title: 'Hike/Trail',
	      colorCodeValue: 'RGB (9, 113, 56)',
	      iconCodeValue: '1596',
	      type: 'hike'
	    },
	    { title: 'Museum',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1636',
	      type: 'museum'
	    },
	    { title: 'Viewpoint/Photo Op',
	      colorCodeValue: 'RGB (57, 73, 171)',
	      iconCodeValue: '1535',
	      type: 'view_photoop'
	    },
	    { title: 'Neighborhood/Area',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1604',
	      type: 'neighborhood'
	    },
	    { title: 'Town',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1547',
	      type: 'town'
	    },
	    { title: 'Church/Religious',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1671',
	      type: 'church_religious'
	    },
	    { title: 'Cemetery',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1542',
	      type: 'cemetery'
	    },
	    { title: 'Store/Shop',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1686',
	      type: 'store_shop'
	    },
	    { title: 'Historic/Ruins',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1598',
	      type: 'historic_ruins'
	    },
	    { title: 'Park/Garden',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1582',
	      type: 'park_garden'
	    },
	    { title: 'Waterfall',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1892',
	      type: 'waterfall'
	    },
	    { title: 'Beach',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1521',
	      type: 'beach'
	    },
	    { title: 'Cinema/Play',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1635',
	      type: 'cinema_play'
	    },
	    { title: 'Monument',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1599',
	      type: 'monument'
	    },
	    { title: 'Fountain/Statue',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1580',
	      type: 'fountain'
	    },
	    { title: 'Artwork',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1509',
	      type: 'artwork'
	    },
	    { title: 'Astronomy',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1878',
	      type: 'astronomy'
	    },
	    { title: 'Cave',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1767',
	      type: 'cave'
	    },
	    { title: 'Geothermal/Hot Springs',
	      colorCodeValue: GMM_ATTRACTION_ATTR_RGB_VALUE,
	      iconCodeValue: '1811',
	      type: 'geothermal'
	    }
	],
	title: 'Attractions'
    },
    [LocationCategory.DINING]: {
	type: LocationCategory.DINING,
	colorCodeValue: 'RGB (251, 192, 45)',
	iconCodeValue: '1577',
	customAttributeList: [
	    CustomAttribute.EXTERNAL_LINKS,
	    CustomAttribute.DESIRABILITY_STATUS,
	    CustomAttribute.RATING,
	    CustomAttribute.PRICE_RANGE
	],
	subcategoryList: [
	    { title: 'Lunch/Dinner',
	      colorCodeValue: 'RGB (251, 192, 45)',
	      iconCodeValue: '1577',
	      type: 'lunch_dinner'
	    },
	    { title: 'Coffee/Breakfast',
	      colorCodeValue: 'RGB (121, 85, 72)',
	      iconCodeValue: '1534',
	      type: 'coffee_breakfast'
	    },
	    { title: 'Deserts/Snacks',
	      colorCodeValue: 'RGB (57, 73, 171)',
	      iconCodeValue: '1607',
	      type: 'deserts'
	    },
	    { title: 'Drinks/Bar',
	      colorCodeValue: 'RGB (156, 39, 176)',
	      iconCodeValue: '1517',
	      type: 'drinks_bar'
	    },
	    { title: 'Food Area',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1611',
	      type: 'food_area'
	    }
	],
	title: 'Dining'
    },
    [LocationCategory.TOWNS]: {
	type: LocationCategory.TOWNS,
	colorCodeValue: 'RGB (165, 39, 20)',
	iconCodeValue: '1603',
	customAttributeList: [
	    CustomAttribute.EXTERNAL_LINKS,
	    CustomAttribute.DESIRABILITY_STATUS
	],
	subcategoryList: [
	],
	title: 'Towns'
    },
    [LocationCategory.LODGING]: {
	type: LocationCategory.LODGING,
	colorCodeValue: 'RGB (194, 24, 91)',
	iconCodeValue: '1602',
	customAttributeList: [
	    CustomAttribute.EXTERNAL_LINKS,
	    CustomAttribute.DESIRABILITY_STATUS,
	    CustomAttribute.BOOKING_STATUS,
	    CustomAttribute.RATING,
	    CustomAttribute.PRICE_RANGE,
	    CustomAttribute.PAYMENT_STATUS,
	    CustomAttribute.LOCATION_FEATURES,
	    CustomAttribute.PAYMENT_DETAILS,
	    CustomAttribute.CANCELLATION_POLICY
	],
	subcategoryList: [
	],
	title: 'Lodging'
    },
    [LocationCategory.TRANSPORTATION_TOURS]: {
	type: LocationCategory.TRANSPORTATION_TOURS,
	colorCodeValue: 'RGB (0, 151, 167)',
	iconCodeValue: '1522',
	customAttributeList: [
	    CustomAttribute.EXTERNAL_LINKS,
	    CustomAttribute.DESIRABILITY_STATUS,
	    CustomAttribute.BOOKING_STATUS,
	    CustomAttribute.RATING,
	    CustomAttribute.PRICE_RANGE,
	    CustomAttribute.LOCATION_FEATURES,
	    CustomAttribute.PAYMENT_DETAILS,
	    CustomAttribute.CANCELLATION_POLICY
	],
	subcategoryList: [
	    { title: 'Plane',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1504',
	      type: 'plane'
	    },
	    { title: 'Car/Auto',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1538',
	      type: 'car_auto'
	    },
	    { title: 'Boat',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1681',
	      type: 'boat'
	    },
	    { title: 'Train',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1716',
	      type: 'train'
	    },
	    { title: 'Cable Car/Funicular',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1533',
	      type: 'cable_car_funicular'
	    },
	    { title: 'Walking',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1596',
	      type: 'walking'
	    },
	    { title: 'Ferry',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1569',
	      type: 'ferry'
	    },
	    { title: 'Bus',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1532',
	      type: 'bus'
	    },
	    { title: 'Bicycle',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1522',
	      type: 'bicycle'
	    },
	    { title: 'Helicopter',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1593',
	      type: 'helicopter'
	    },
	    { title: 'Parking',
	      colorCodeValue: 'RGB (0, 151, 167)',
	      iconCodeValue: '1644',
	      type: 'parking'
	    }
	],
	title: 'Transportation/Tours'
    }
};    


const LOCATION_CATEGORY_LIST = [];
const LOCATION_CATEGORY_MAP = {};
const LOCATION_CATEGORY_BY_TITLE_MAP = {};
const LOCATION_SUBCATEGORY_MAP = {};
const LOCATION_SUBCATEGORY_BY_ICON_CODE_MAP = {};


for ( let locationCategory in LocationCategoryDef ) {
    let categoryDef = LocationCategoryDef[locationCategory];
    LOCATION_CATEGORY_LIST.push( categoryDef );
    LOCATION_CATEGORY_MAP[categoryDef.type] = categoryDef;
    LOCATION_CATEGORY_BY_TITLE_MAP[categoryDef.title] = categoryDef;
    for ( let sub_idx = 0; sub_idx < categoryDef.subcategoryList.length; sub_idx++ ) {
	let subcategory = categoryDef.subcategoryList[sub_idx];
	LOCATION_SUBCATEGORY_MAP[subcategory.type] = subcategory;
	LOCATION_SUBCATEGORY_BY_ICON_CODE_MAP[subcategory.iconCodeValue] = subcategory;
    }    
    
}


// ============================================================
// Dialog Modifications 

function addToMapButtonId( categoryName ) {
    return 'vt-add-to-map-' + categoryName;
}


// Function to add custom button to a dialog
function decorateAddToMapDialog( dialogElement ) {
    console.log( 'Decorating add-to-map dialog. Id = ' + dialogElement.id );


    // find add to map button, then get its parent
    let addToMapButton = dialogElement.querySelector( '#' + GMM_ADD_TO_MAP_BUTTON_ID );
    if ( ! addToMapButton ) {
	console.error( 'Could not find add-to-map button in dialog.' );
	return;
    }
    
    let container = addToMapButton.parentNode;

    LOCATION_CATEGORY_LIST.forEach( categoryDef => {
	let button = document.createElement('button');
	button.id = addToMapButtonId( categoryDef.type );
	button.textContent = categoryDef.title;
	button.addEventListener('click', function() {
	    handleAddToLocationButtonClick( dialogElement, categoryDef.type );
	});
	container.appendChild(button);
    });
    console.log( 'Finished decorating add-to-map dialog' );
}


// Function to add custom button to a dialog
async function decorateLocationDetailsDialog( dialogElement ) {

    let titleNode = document.getElementById( GMM_TITLE_DIV_ID );
    
    const locationTitle = titleNode.textContent;
    const layerLocationInfo = getLocationInfoFromLayers( locationTitle );
    if ( ! layerLocationInfo ) {
	console.error( 'Problem finding locationInfo in layers for: '
		       + locationTitle );
	return;
    }

    let locationInfo = await upsertLocationInfo( layerLocationInfo );
    if ( ! locationInfo ) {
	console.error( 'No stored location info found: ' + locationTitle );
	return;
    }
    if ( ! locationInfo.locationCategory ) {
	console.error( 'Cannot determine location category for: '
		       + locationTitle );
	return;
    }

    const isEditMode = ( titleNode.getAttribute('contenteditable') == 'true' );
    if ( isEditMode ) {
	replaceAttributeSaveButton();
    }
    addCustomAttributes( locationInfo, isEditMode );
    return;
}


// ============================================================
// Google My Maps (GMM) page DOM Constants

const GMM_ADD_TO_MAP_BUTTON_ID = 'addtomap-button';

const GMM_INFO_CONTAINER_ID = 'map-infowindow-container';
const GMM_EDIT_BUTTON_ID = 'map-infowindow-edit-button';
const GMM_STYLE_BUTTON_ID = 'map-infowindow-style-button';
const GMM_STYLE_CLOSE_BUTTON_ID = 'stylepopup-close';
const GMM_TITLE_DIV_ID = 'map-infowindow-attr-name-value';
const GMM_NOTES_DIV_ID = 'map-infowindow-attr-description-value';
const GMM_NOTES_CONTAINER_ID = "map-infowindow-attr-description-container";
const GMM_EDIT_SAVE_BUTTON_ID = 'map-infowindow-done-editing-button';

const GMM_ADD_LAYER_BUTTON_ID = 'map-action-add-layer';
const GMM_LAYER_OPTIONS_MENU_ID = 'layerview-menu';
const GMM_LAYER_UPDATE_DIALOG_ID = 'update-layer-name';

const GMM_LAYER_ID_ATTRIBUTE = 'layerid';
const GMM_LAYER_SELECTOR = '#featurelist-scrollable-container div[' + GMM_LAYER_ID_ATTRIBUTE + ']';

const GMM_LAYER_OPTIONS_ATTRIBUTE_NAME = 'item';
const GMM_LAYER_OPTIONS_RENAME_VALUE = 'rename-layer';
const GMM_LOCATION_EDIT_NAME_SELECTOR = 'input[type="text"]';
const GMM_LOCATION_EDIT_SAVE_SELECTOR = 'button[name="save"]';

const GMM_LOCATION_ITEM_ID_ATTRIBUTE = 'fl_id';
const GMM_LOCATION_ITEMS_SELECTOR = 'div[' + GMM_LOCATION_ITEM_ID_ATTRIBUTE + ']';


// ============================================================
// GMM Locations


function handleAddToLocationButtonClick( dialogElement, locationCategoryType ) {

    console.log( 'Handling add-to-map click.' );
    let locationCategory = LOCATION_CATEGORY_MAP[locationCategoryType];

    if ( locationCategory.subcategoryList.length > 0 )  {
	showSubcategoryPicker( dialogElement, locationCategory );
    }
    else {
	addLocationToMap( dialogElement, locationCategory );
    }
}


async function showSubcategoryPicker( dialogElement, locationCategory ) {

    const templateUrl = chrome.runtime.getURL('templates/subcategory-picker-dialog.html');
    console.log( 'Template URL = ' + templateUrl );

    fetch( templateUrl )
        .then( response => response.text())
        .then( template => {
	    
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = template;
            const buttonContainer = tempDiv.querySelector('#vt-subcategory-picker-dialog-container');
            const cancelButton = tempDiv.querySelector('#vt-cancel-button');

	    for( let i = 0; i < locationCategory.subcategoryList.length; i++ ) {
		let subcategory = locationCategory.subcategoryList[i];
		
		let subcategoryButton = document.createElement('button');
		subcategoryButton.textContent = subcategory.title;
		subcategoryButton.addEventListener('click', () => {
                    document.body.removeChild(tempDiv);
		    addLocationToMap( dialogElement, locationCategory, subcategory );
		});
		buttonContainer.appendChild( subcategoryButton );
	    }
            cancelButton.addEventListener('click', () => {
                document.body.removeChild(tempDiv);
            });
            document.body.appendChild(tempDiv);
        })
        .catch( error => {
            console.error('Fetch error:', error);
	});
}


async function addLocationToMap( dialogElement, locationCategory, subcategory = null ) {

    console.log( 'Adding location to: ' + locationCategory.title );
    
    let addToMapButton = document.querySelector( '#' + GMM_ADD_TO_MAP_BUTTON_ID );
    if ( addToMapButton == null ) {
	console.error( 'No DOM element found for id = '
		       + GMM_ADD_TO_MAP_BUTTON_ID );
	return;
    }

    try {
	await selectLocationLayer( locationCategory, true );
	await simulateClick( addToMapButton );

	const titleNode = await waitForElement( '#map-infowindow-attr-name-value' );
	const locationTitle = titleNode.textContent;
	console.log( 'Location added: ' + locationTitle );
	
	let locationId = getLocationIdFromLayers( locationTitle );
	if ( locationId ) {
	    await upsertLocationInfo({
		locationId: locationId,
		title: locationTitle,
		locationCategory: locationCategory,
		subcategory: subcategory
	    });
	} else {
	    console.error( 'Problem finding locationId in layers for: '
			   + locationTitle );
	}
	
	const styleButton = await waitForElement( '#' + GMM_STYLE_BUTTON_ID );	
	
	console.log( 'Clicking style button:' );
	console.log( styleButton );
	await simulateClick( styleButton );
	
	await setLocationColor( locationCategory, subcategory );
	await setLocationIcon( locationCategory, subcategory );

	let styleCloseButton = document.getElementById( GMM_STYLE_CLOSE_BUTTON_ID );
	console.log( styleCloseButton );
	await simulateRealisticClick( styleCloseButton );
	
    } catch (error) {
        console.error( error.message );
	throw error;
    }

    // Scrolling to elemements can leave leave screen out of whack.
    const sidebar = document.querySelector( '#featurelist-pane' );
    sidebar.scrollIntoView();    
}


async function setLocationColor( locationCategory, subcategory ) {

    console.log( 'Setting location color' );
    
    let selector = '#stylepopup-color td > div';
    let ariaLabelValue = locationCategory.colorCodeValue;
    if ( subcategory != null ) {
	ariaLabelValue = subcategory.colorCodeValue;
    }
    
    const elements = document.querySelectorAll(selector);

    let colorElement;
    for ( let i = 0; i < elements.length; i++) {
	let element = elements[i];
	if ( element.getAttribute('aria-label') == ariaLabelValue  ) {
	    colorElement = element;
	    break;
	}
    }

    if ( colorElement ) {
	await simulateRealisticClick( colorElement );
    } else {
	// TODO: If color not found by RGB value, it could be due to Google
	// tweaking it.  Add a backup strategy that grabs the colow by the
	// position since that might be less likely to move around.
	console.error( 'Color not found with value: ' + ariaLabelValue );
    }
}


async function setLocationIcon( locationCategory, subcategory ) {

    let iconCodeValue = locationCategory.iconCodeValue;
    if ( subcategory != null ) {
	iconCodeValue = subcategory.iconCodeValue;
    }
    console.log( 'Setting location icon: ' + iconCodeValue );

    const styleDialog = document.querySelector( '#stylepopup-container' );
    let iconElement = getLocationIconElement( styleDialog, iconCodeValue );
    
    if ( iconElement ) {
	await simulateRealisticClick( iconElement );
    } else {
	console.log( 'Icon (initial) not found: ' + iconCodeValue );
	await setLocationIconMoreIcons( locationCategory, subcategory );
    }
}


async function setLocationIconMoreIcons( locationCategory, subcategory ) {

    let iconCodeValue = locationCategory.iconCodeValue;
    if ( subcategory != null ) {
	iconCodeValue = subcategory.iconCodeValue;
    }
    console.log( 'Setting location icon: ' + iconCodeValue );

    const styleDialog = document.querySelector( '#stylepopup-container' );
    let moreIconsOpenButton = styleDialog.querySelector( '#stylepopup-moreicons-button' );
    await simulateRealisticClick( moreIconsOpenButton );
    await wait( 1000 );
	
    const element = document.querySelector( '#iconspopup-category-target-1' );
    const moreIconsDialog = element.parentNode.parentNode;
    let iconElement = getLocationIconElement( moreIconsDialog, iconCodeValue );

    if ( iconElement == null ) {
	console.error( 'Icon (more) not found: ' + iconCodeValue );
	return;
    }

    await simulateRealisticClick( iconElement.firstChild );

    let moreIconsCloseButton = moreIconsDialog.querySelector( 'button[name="ok"]' );
    await simulateRealisticClick( moreIconsCloseButton );
}


function getLocationIconElement( node, iconCodeValue ) {

    console.log( 'Looking for icon: ' + iconCodeValue );
    console.log( node );
    
    const elements = node.querySelectorAll( 'div[iconcode]' );
    
    for ( let i = 0; i < elements.length; i++) {
	let iconElement = elements[i];
	if ( iconElement.getAttribute('iconcode') == iconCodeValue  ) {
	    console.log( 'Found icon: ' + iconCodeValue );
	    console.log( iconElement );
	    return iconElement;
	}
    }
    return null;
}


// ============================================================
// Models


function LayerInfo({ title,
		     layerId = null,
		     layerNode = null,
		     locationInfoList = null }) {

    this.title = title;
    this.layerId = layerId;
    this.layerNode = layerNode;
    this.locationInfoList = locationInfoList;
    
    if ( this.locationInfoList == null ) {
	this.locationInfoList = [];
    }
}


function LocationInfo( title,
		       locationId,
		       locationCategory,
		       subcategory,
		       customAttributes = null ) {
    this.title = title;
    this.locationId = locationId;
    this.locationCategory = locationCategory;
    this.subcategory = subcategory;
    
    if ( customAttributes ) {
	for( let attrName in customAttributes ) {
	    this[attrName] = customAttributes[attrName];
	}
    }
}


LocationInfo.prototype.update = function({ title = null,
					   locationCategory = null,
					   subcategory = null,
					   customAttributes = null }) {    

    function shouldUpdate( currentObject, updateObject, key = null ) {
	if ( updateObject == null ) { return false; }
	if ( currentObject == null ) { return true; }

	let currentValue, updateValue;
	if ( key ) {
	    currentValue = currentObject[key];
	    updateValue = updateObject[key];
	} else {
	    currentValue = currentObject;
	    updateValue = updateObject;
	}
	return ( currentValue != updateValue );
    }
    
    let changed = false;
    
    if ( shouldUpdate( this.title, title )) {
	this.title = title;
	changed = true;
    }
    if ( shouldUpdate( this.locationCategory, locationCategory, 'type' )) {
	this.locationCategory = locationCategory;
	changed = true;
    }
    if ( shouldUpdate( this.subcategory, subcategory, 'type' )) {
	this.subcategory = subcategory;
	changed = true;
    }

    if ( customAttributes ) {
	 for( let attrName in customAttributes ) {
	     const attrValue = customAttributes[attrName];
	     if ( shouldUpdate( this[attrName], attrValue )) {
		 this[attrName] = attrValue;
		 changed = true;
	     }
	 }
    }

    console.log( 'Updated Location: changed = ' + changed );
    console.log( this );
    return changed;
};


LocationInfo.prototype.toStoredData = function() {
    let categoryType = null;
    let subcategoryType = null;
    
    if ( this.locationCategory ) {
	categoryType = this.locationCategory.type;
    }
    if ( this.subcategory ) {
	subcategoryType = this.subcategory.type;
    }
    
    let storedData = {
	title: this.title,
	locationId: this.locationId,
	categoryType: categoryType,
	subcategoryType: subcategoryType,
    };
    for( let attrName in CustomAttributeDef ) {
	storedData[attrName] = this[attrName];
    }
    return storedData;
};


function locationInfoFromStoredData( storedData ) {

    let locationCategory = null;
    let subcategory = null;

    if ( storedData.categoryType ) {
	locationCategory = LOCATION_CATEGORY_MAP[storedData.categoryType];
    }
    if ( storedData.subcategoryType ) {
	subcategory = LOCATION_SUBCATEGORY_MAP[storedData.subcategoryType];
    }

    let customAttributes = {};
    for( let attrName in CustomAttributeDef ) {
	customAttributes[attrName] = storedData[attrName];
    }
    return new LocationInfo(
	storedData.title,
	storedData.locationId,
	locationCategory,
	subcategory,
	customAttributes
    );
    
};


// ============================================================
// Storage


function getLocationKey( locationId ) {
    // TODO: Should add the map id to this key to prevent collisions on
    // the storage keys.  I am not sure if the "flId" value in the DOM
    // is globally unique or not.

    return "vtLocation:" + locationId;
}


async function upsertLocationInfo({ locationId,
				    title,
				    locationCategory = null,
				    subcategory = null }) {
    try {
	const locationKey = getLocationKey( locationId );
	let changed = false;
	let locationInfo;

	const storedData = await chrome.storage.local.get({ [locationKey]: {} });
	console.log( '[upsert] Stored Data for: ' + locationId );
	console.log( storedData );
	
	if ( ! storedData[locationKey].locationId ) {
	    console.log( '[upsert] Location not found in storage: ' + locationId );
	    locationInfo = new LocationInfo(
		title,
		locationId,
		locationCategory,
		subcategory		    
	    );
	    changed = true;
	} else {
	    locationInfo = locationInfoFromStoredData( storedData[locationKey] );
	    console.log( '[upsert] Found Location in storage:' );
	    console.log( locationInfo );

	    // Handling legacy stored data
	    if ( ! locationInfo.locationId ) {
		locationInfo.locationId = locationId;
		console.log( 'Force filling locationId' );
	    }
	    
	    changed = locationInfo.update({
		title: title,
		locationCategory: locationCategory,
		subcategory: subcategory
	    });
	}
	    
	if ( changed ) {
	    console.log( '[upsert] Updating location storage: ' + locationId );
	    console.log( locationInfo );
	    const updatedStoredData = locationInfo.toStoredData();
	    console.log( '[upsert] Storing Location:' );
	    console.log( updatedStoredData );
	    await chrome.storage.local.set( { [locationKey]: updatedStoredData });
	}
	return locationInfo;
	
    } catch (error) {
	console.error('Error in upsertLocationInfo:', error);
	throw error;
    }
}


async function updateCustomAttributes( locationId, customAttributes ) {

    const locationKey = getLocationKey( locationId );
    const storedData = await chrome.storage.local.get({ [locationKey]: {} });

    if ( ! storedData[locationKey].locationId ) {
	console.error( '[update] Location not found in storage: ' + locationId );
	return;
    }

    let locationInfo = locationInfoFromStoredData( storedData[locationKey] );
    console.log( '[update] Found Location in storage:' );
    console.log( locationInfo );
    locationInfo.update({ customAttributes: customAttributes });
    
    const updatedStoredData = locationInfo.toStoredData();
    console.log( '[update] Storing Location:' );
    console.log( updatedStoredData );
    await chrome.storage.local.set( { [locationKey]: updatedStoredData });
}


// ============================================================
// GMM Layers


function getLocationIdFromLayers( locationTitle ) {
    let locationInfo = getLocationInfoFromLayers( locationTitle );
    if ( locationInfo == null ) {
	return null;
    }
    return locationInfo.locationId;
}


function getLocationInfoFromLayers( locationTitle ) {

    // TODO: The location title may not be unique.  Thus, matching on title
    // may not always give the desired result.  This needs a solution in
    // order to do the right thing in the face of duplicate titles.
    
    let layerInfoList = getLayerInfoList();
    for ( let layer_idx = 0; layer_idx < layerInfoList.length; layer_idx++ ) {
	let layerInfo = layerInfoList[layer_idx];
	for ( let location_idx = 0; location_idx < layerInfo.locationInfoList.length; location_idx++ ) {
	    let locationInfo = layerInfo.locationInfoList[location_idx];
	    if ( locationInfo.title == locationTitle ) {
		return locationInfo;
	    }
	}
    }
    return null;
}


function getLayerInfoList() {

    let layerInfoList = [];

    const elements = document.querySelectorAll( GMM_LAYER_SELECTOR );
    for ( let i = 0; i < elements.length; i++ ) {
	let layerNode = elements[i];
	let headerNode = layerNode.childNodes[0];
	let locationContainerNode = layerNode.childNodes[3];
	let titleNode = headerNode.childNodes[1];

	const layerTitle = titleNode.textContent;
	const locationCategory = LOCATION_CATEGORY_BY_TITLE_MAP[layerTitle];

	let layerInfo = new LayerInfo({
	    title: layerTitle,
	    locationCategory: locationCategory,
	    layerId: layerNode.getAttribute( GMM_LAYER_ID_ATTRIBUTE ),
	    layerNode: layerNode,
	    locationInfoList: getLayerLocationInfoList( layerNode, locationCategory ),
	});
	layerInfoList.push( layerInfo );
    }
    return layerInfoList;
}


function getLayerLocationInfoList( layerNode, locationCategory ) {

    let locationInfoList = [];
    let subcategory = null;
    
    let elements = layerNode.querySelectorAll( GMM_LOCATION_ITEMS_SELECTOR );
    for ( let i = 0; i < elements.length; i++ ) {
	let locationNode = elements[i];
	let iconNode = locationNode.childNodes[0];
	let titleNode = locationNode.childNodes[1].firstChild;

	if ( locationCategory
	     && ( locationCategory.subcategoryList.length > 0 )) {

	    let iconCodeNode = iconNode.querySelector( 'div[iconcode]' );
	    let iconCodeColorCombo = iconCodeNode.getAttribute('iconcode');
	    let iconCode = iconCodeColorCombo.split('-')[0];
	    subcategory = LOCATION_SUBCATEGORY_BY_ICON_CODE_MAP[iconCode];
	}
	
	let locationInfo = new LocationInfo( 
	    titleNode.textContent,
	    locationNode.getAttribute( GMM_LOCATION_ITEM_ID_ATTRIBUTE ),
	    locationCategory,
	    subcategory
	);
	locationInfoList.push( locationInfo );
    }

    return locationInfoList;
}


async function selectLocationLayer( locationCategory, createIfMissing ) {

    let layerNode = await getLocationLayer( locationCategory, createIfMissing );
    if ( layerNode == null ) {
	return;
    }
    let headerNode = layerNode.firstChild;
    let titleNode = headerNode.childNodes[1];
    await simulateRealisticClick( titleNode );
}


async function getLocationLayer( locationCategory, createIfMissing = false ) {
    
    const elements = document.querySelectorAll( GMM_LAYER_SELECTOR );
    
    for ( let i = 0; i < elements.length; i++ ) {
	let element = elements[i];
	
	let headerNode = element.firstChild;
	let titleNode = headerNode.childNodes[1];
	
	if ( titleNode.textContent == locationCategory.title ) {
	    console.log( 'Layer found' );
	    console.log( element );
	    return element;
	}
    }
    console.log( 'Layer not found: ' + locationCategory.title );
    if ( createIfMissing ) {
	return await createLocationLayer( locationCategory );
    }
    return null;
}


async function createLocationLayer( locationCategory ) {

    console.log( 'Creating layer: ' + locationCategory.title );
    
    let addLayerButton = document.getElementById( GMM_ADD_LAYER_BUTTON_ID );

    await simulateRealisticClick( addLayerButton );
    await wait( 2000 );
    
    // Assumes the new layer is added to the end.
    const elements = document.querySelectorAll( GMM_LAYER_SELECTOR );
    let latestLayerNode = elements[elements.length - 1];

    console.log( 'Latest Layer:' );
    console.log( latestLayerNode );
    
    await renameLocationLayer( latestLayerNode, locationCategory.title );
    return latestLayerNode;
}


async function renameLocationLayer( layerNode, layerName ) {

    console.log( 'Renaming layer: ' + layerName );
    console.log( layerNode );
    
    let headerNode = layerNode.firstChild;
    let menuNode = headerNode.childNodes[2];

    await simulateClick( menuNode );

    // These have ids, but they are no unique. Seems it create a new entry
    // in the DOM for each layer.  A bug on Google's part I suspect.
    let visibleNodes = getVisibleNodes( '#' + GMM_LAYER_OPTIONS_MENU_ID );

    if ( visibleNodes.length < 1 ) {
	console.error( 'No options menu for layer: ' + layerName );
	return;
    }
    
    if ( visibleNodes.length > 1 ) {
	console.log( 'Multiple option menus found:' );
	visibleNodes.forEach( node => {
	    console.log( node );
	});
    }

    // New ones usually added at the end.
    let optionsMenu = visibleNodes[visibleNodes.length - 1];

    for ( let i = 0; i < optionsMenu.childNodes.length; i++ ) {
	let childNode = optionsMenu.childNodes[i];

	console.log( 'Checking options menu child' );
	console.log( childNode );
	
	if ( childNode.getAttribute(GMM_LAYER_OPTIONS_ATTRIBUTE_NAME)
	     == GMM_LAYER_OPTIONS_RENAME_VALUE ) {

	    await simulateRealisticClick( childNode );
	    
	    let updateDialog = await waitForElement( '#' + GMM_LAYER_UPDATE_DIALOG_ID );
	    let layerNameInput = updateDialog.querySelector( GMM_LOCATION_EDIT_NAME_SELECTOR );
	    let saveButton = updateDialog.querySelector( GMM_LOCATION_EDIT_SAVE_SELECTOR );

	    console.log( 'Found update dialog' );
	    console.log( updateDialog );
	    console.log( layerNameInput );
	    console.log( saveButton );

	    layerNameInput.value = layerName;
	    await simulateClick( saveButton );

	    break;
	}
    }
    
}



// ============================================================
// General DOM manipulation helpers


const DOM_CLICK_DELAY_MS = 500;
const DOM_ELEMENT_WAIT_MS = 3000;


function wait( durationMs = 250 ) {
    return new Promise((resolve) => {
        setTimeout( resolve, durationMs );
    });
}


function simulateClick( element, delayMs = DOM_CLICK_DELAY_MS ) {
    return new Promise((resolve) => {
        element.click();
        setTimeout( resolve, delayMs );
    });
}


function waitForElement( selector, nodeScope = document ) {
    
    return new Promise( ( resolve, reject ) => {
        if ( nodeScope.querySelector( selector )) {
            return resolve( nodeScope.querySelector( selector ));
        }
        const observer = new MutationObserver( mutations => {
	    console.log( 'Waiting mutation observer called.' );
	    let querySelectorResult = nodeScope.querySelector( selector );
            if ( querySelectorResult ) {
                observer.disconnect();
                resolve( querySelectorResult );
            }
        });

        observer.observe( nodeScope.body, {
            childList: true,
            subtree: true
        });

	setTimeout(() => {
            observer.disconnect();
            reject( new Error('Element did not appear within time limit: '
			      + selector ));
	}, DOM_ELEMENT_WAIT_MS );
	
    });    
}


function waitForNotElement( selector, nodeScope = document ) {

    return new Promise( ( resolve, reject ) => {
        if ( ! nodeScope.querySelector( selector )) {
            return resolve( true );
        }
        const observer = new MutationObserver( mutations => {
	    console.log( 'Waiting mutation observer called.' );
	    let querySelectorResult = nodeScope.querySelector( selector );
            if ( ! querySelectorResult ) {
                observer.disconnect();
                resolve( true );
            }
        });

        observer.observe( nodeScope.body, {
            childList: true,
            subtree: true
        });

	setTimeout(() => {
            observer.disconnect();
            reject( new Error('Element persists within time limit: '
			      + selector ));
	}, DOM_ELEMENT_WAIT_MS );
	
    });    
}


async function simulateRealisticClick( element ) {
    // Use this is troublesome issue with calling just .click()
    
    if (!element) return;

    const scrollX = window.scrollX;
    const scrollY = window.scrollY;

    element.scrollIntoView();
    await wait( 500 );
    
    const mouseEventInit = {
        view: window,
        bubbles: true,
        cancelable: true
    };
    const mouseDownEvent = new MouseEvent('mousedown', mouseEventInit);
    const mouseUpEvent = new MouseEvent('mouseup', mouseEventInit);
    const clickEvent = new MouseEvent('click', mouseEventInit);
    
    // Dispatch the events
    element.dispatchEvent(mouseDownEvent);
    element.dispatchEvent(mouseUpEvent);
    element.dispatchEvent(clickEvent);

    window.scrollTo(scrollX, scrollY);
    await wait( 500 );
}


function getVisibleNodes( selector ) {
    let elements = document.querySelectorAll( selector );

    console.log( 'All elements for selector = ' + selector );
    elements.forEach( node => {
	console.log( node );
    });
    
    let visibleElements = Array.from(elements).filter(el => {
	let style = window.getComputedStyle(el);
	return style.display !== 'none' && 
            style.visibility !== 'hidden' &&
            el.offsetWidth > 0 && 
            el.offsetHeight > 0;
    });

    console.log( 'Visible elements for selector = ' + selector );
    visibleElements.forEach( node => {
	console.log( node );
    });
        
    return visibleElements;
}



// ============================================================
// Location Attribute Form Elements

const VT_ATTRIBUTES_TEXT_IFRAME_ID = 'vt-attr-text-iframe';
const VT_ATTRIBUTES_TEXT_IFRAME_CLASS = 'vt-location-attributes';
const VT_LOCATION_ID_ATTR_ID = 'vt-attr-location-id';


function addCustomAttributes( locationInfo, isEditMode ) {

    if ( document.getElementById( VT_LOCATION_ID_ATTR_ID )) {
	return;
    }
    
    // Insert notes label to the existing notes/description text since we
    // will now be adding additional input boxes to show.
    let notesContainer = document.getElementById( GMM_NOTES_CONTAINER_ID );

    const hiddenIdNode = document.createElement('input');
    hiddenIdNode.id = VT_LOCATION_ID_ATTR_ID;
    hiddenIdNode.type = 'hidden';
    hiddenIdNode.name = VT_LOCATION_ID_ATTR_ID;
    hiddenIdNode.value = locationInfo.locationId;
    notesContainer.append( hiddenIdNode );
    
    // Some attributes we show above notes, and the textual editable notes
    // we show below.

    const notesLabel = document.createElement('div');
    notesLabel.textContent = 'Notes';
    notesContainer.insertBefore( notesLabel, notesContainer.firstChild );

    const nonTextAttributeNode = document.createElement('div');
    notesContainer.parentNode.insertBefore( nonTextAttributeNode,
					    notesContainer);
    addNonTextAttributes( locationInfo,
			  document,
			  nonTextAttributeNode,
			  isEditMode );

    // The Backspace key is tied to deleting the location from the map.
    // This was a problem for the editable text we needed to insert as
    // one could not edit the text using the backspace. Worst is that it
    // would delete the location from the map entirely.  Everything tried
    // was not able to wrest control from the event handler that is tying
    // the backspace to the location deletion.  The workaround was to use
    // an iframe to have our inserted content have an isolated event
    // environment.
    //
    const textAttributeIframe = document.createElement('iframe');
    textAttributeIframe.id = VT_ATTRIBUTES_TEXT_IFRAME_ID;
    textAttributeIframe.src = 'about:blank';
    textAttributeIframe.classList.add( VT_ATTRIBUTES_TEXT_IFRAME_CLASS );
    if ( notesContainer.nextSibling ) {
	notesContainer.parentNode.insertBefore( textAttributeIframe,
						notesContainer.nextSibling);
    } else {
	notesContainer.parentNode.appendChild( textAttributeIframe );
    }
    const iframeDocument = textAttributeIframe.contentDocument || textAttributeIframe.contentWindow.document;
    addTextAttributes( locationInfo,
		       iframeDocument,
		       iframeDocument.body,
		       isEditMode );
}


function addNonTextAttributes( locationInfo,
			       parentDocument,
			       parentNode,
			       isEditMode ) {
    const newNode = parentDocument.createElement('div');
    newNode.textContent = 'Non-text Attributes';

    const customAttributeList = locationInfo.locationCategory.customAttributeList;
    for( let idx = 0; idx < customAttributeList.length; idx++  ) {
	const customAttribute = customAttributeList[idx];
	const customAttributeDef = CustomAttributeDef[customAttribute];

	let attrNode = null;
	if (customAttributeDef.type === CustomAttributeType.DROP_DOWN ) {
	    attrNode = locationAttributeDropDown( locationInfo,
						  customAttributeDef,
						  parentDocument );
	}
	if ( attrNode ) {
	    newNode.appendChild( attrNode );
	}
    }
    parentNode.appendChild( newNode );
}


function addTextAttributes( locationInfo,
			    parentDocument,
			    parentNode,
			    isEditMode ) {
    const newNode = parentDocument.createElement('div');
    newNode.textContent = 'Text Attributes';

    const customAttributeList = locationInfo.locationCategory.customAttributeList;
    for( let idx = 0; idx < customAttributeList.length; idx++  ) {
	const customAttribute = customAttributeList[idx];
	const customAttributeDef = CustomAttributeDef[customAttribute];
	
	let attrNode = null;
	if (customAttributeDef.type === CustomAttributeType.TEXT_AREA ) {
	    attrNode = locationAttributeTextarea( locationInfo,
						  customAttributeDef,
						  parentDocument,
						  isEditMode );
	}
	if ( attrNode ) {
	    newNode.appendChild( attrNode );
	}
    }
    parentNode.appendChild( newNode );
}


function locationAttributeDropDown( locationInfo,
				    customAttributeDef,
				    parentDocument ) {
    const newNode = parentDocument.createElement('div');
    const dropdown = parentDocument.createElement('select');
    const dropdownId = 'vt-dropdown-' + customAttributeDef.name;
    dropdown.id = dropdownId;

    for ( const attrValue in customAttributeDef.valuesDef ) {
	const valueDef = customAttributeDef.valuesDef[attrValue];
	const option = parentDocument.createElement('option');
	option.value = attrValue;
	option.text = valueDef.label;
	dropdown.appendChild( option );
    }

    dropdown.value = locationInfo[customAttributeDef.name];
    
    const label = parentDocument.createElement('label');
    label.textContent = customAttributeDef.label;
    label.setAttribute('for', dropdownId);

    newNode.appendChild( label );
    newNode.appendChild( dropdown );

    function updateDropDown() {
	const attrValue = dropdown.value;
	console.log( 'Selected ' + customAttributeDef.label + ': ' + attrValue );
	const customAttributes = { [customAttributeDef.name]: attrValue };
	updateCustomAttributes( locationInfo.locationId, customAttributes );
    }
    dropdown.addEventListener('change', updateDropDown);

    return newNode;
}





function locationAttributeTextarea( locationInfo,
				    customAttributeDef,
				    parentDocument,
				    isEditMode ) {
    const newNode = parentDocument.createElement('div');
    const attrName = customAttributeDef.name;
    
    let textarea;
    if ( isEditMode ) {
	textarea = parentDocument.createElement('textarea');
	textarea.id = customAttributeElementId( attrName ),
	textarea.rows = 2;
	textarea.cols = 35;
	textarea.contentEditable = true;
	if ( locationInfo[attrName] ) {
	    textarea.value = locationInfo[attrName];
	}
    } else {
	if ( ! locationInfo[attrName] ) {
	    return emptyElement( parentDocument );
	}
	textarea = parentDocument.createElement('div');
	textarea.textContent = locationInfo[attrName];
    }
    
    const label = parentDocument.createElement('label');
    label.textContent = customAttributeDef.label;
    newNode.appendChild(label);
    newNode.appendChild(textarea);
    return newNode;
}



function customAttributeElementId( attrName ) {
    return 'vt=attr-value-' + attrName;
}


function emptyElement( parentDocument ) {
    const hiddenElement = parentDocument.createElement('div');
    hiddenElement.style.display = 'none';
    return hiddenElement;
}


function replaceAttributeSaveButton() {
    // Since we want to save extra attributes when the "save" button is
    // clicked, we have to intercept the button click. Simply adding a new
    // event listener to the button does not suffice since we cannot
    // control the order that the event handlers are called.  Thus, if the
    // original one is called first (which is likely since they get called
    // in order of addition), the form elements we added may have been
    // remove from the DOM as the dialog gets updated. Thus, we replace the
    // existing button so that we can do our work first, then delegate to
    // the original button's event handlers.

    const existingButton = document.getElementById( GMM_EDIT_SAVE_BUTTON_ID );
    if ( ! existingButton) {
	console.error( 'Could not find save button.' );
	return;
    }
    const newButton = existingButton.cloneNode( true );
    newButton.id = null;
    
    async function handleNewButtonClick(event) {
	console.log('VT Save Button Clicked');
	try {
	    await handleCustomAttributeSave();
	    
	} catch (error) {
            console.error( error.message );
	}
	existingButton.firstChild.click();
    }
    newButton.addEventListener('click', handleNewButtonClick );
    existingButton.style.display = 'none';
    existingButton.insertAdjacentElement( 'afterend', newButton );
}


async function handleCustomAttributeSave() {

    const hiddenIdNode = document.getElementById( VT_LOCATION_ID_ATTR_ID );
    if ( ! hiddenIdNode ) {
	console.error( 'Could not find location id hidden node for saving.' );
	return;
    }
    const locationId = hiddenIdNode.value;
    console.log( 'Handling Location Attribute Save for: ' + locationId );
	  
    let cancellationPolicy = null;


    let textAttributeIframe = document.getElementById( VT_ATTRIBUTES_TEXT_IFRAME_ID );
    const iframeDocument = textAttributeIframe.contentDocument || textAttributeIframe.contentWindow.document;

    let customAttributes = {};
    for( let attrName in CustomAttributeDef ) {
	const textAreaId = customAttributeElementId( attrName );
	const textarea = iframeDocument.getElementById( textAreaId );
	if ( textarea ) {
	    customAttributes[attrName] = textarea.value;
	}
    }
    console.log( 'Custom attributes for update:' );
    console.log( customAttributes );
    await updateCustomAttributes( locationId, customAttributes );
}
