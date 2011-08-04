function logout(){
    FB.logout(
        function(response) {
            willet.functions.store.clean();
            window.location = "/seller";
        });
    willet.functions.store.clean();
};

function getPaid( ) {
    $.ajax({
        url: "/seller/doGetPaid",
        type: "POST",
        data: ({}),
        success: function( response ) {
            alert( 'A Customer Service representative will contact you via email shortly to determine a method for payment.' );
        },
        failure: function( response ) {
            alert( 'There was an error. Please email contact@getwillet.com to sort it out.' );
        }
    });
};


// document.getElementById("webapp-button").OnMouseOver = function(e){
//     document.getElementById("webapp-text").style.display="block";
// };
//document.getElementById('webapp-button').onmoustout = hideHelpText('webapp-text');
function clearHelpText()
{

    try{
        // default_help_text exists in both creatoffer and offer choice
        document.getElementById('default_help_text').style.display="none";

        // these do not exist on createOffer.html so it will fail but that is ok
        document.getElementById('webapp-text').style.display="none";
        document.getElementById('feature-text').style.display="none";
        document.getElementById('content-text').style.display="none";

    }catch(err){
        return true;
    }

}

function showHelpText(helpTextName)
{
    clearHelpText();
    document.getElementById(helpTextName).style.display="inline";
};

function hideHelpText(helpTextName)
{
    clearHelpText();
    document.getElementById(helpTextName).style.display="none";
    document.getElementById('default_help_text').style.display="inline";
};


function putHttpInField() {
    var url_field = document.getElementById( 'url' );
    url_field.value = "http://";
};


function appendCent( elem, focus ) {
    var curr_val = elem.value;

    if ( curr_val.indexOf( '¢' ) === -1 ) {
        elem.value = elem.value + '¢';
    }

    if ( focus ) {
        $(elem).get(0).setSelectionRange( 0, 0 );
    }
};

function removeCent( elemId ) {
    var elem = document.getElementById( elemId );
    var curr_val = elem.value;

    elem.value = curr_val.replace('¢','');
};

function testWebhook( offerUuid ) {
    $.ajax({
        url: "/sell/doTestWebhook",
        type: "POST",
        data: ({'offer_uuid' : offerUuid}),
        success: function( response ) {
            alert( 'POST data sent. Go check your logs! \r\nHere\'s what we received:\r\n' + response );
        },
        statusCode: {
            500: function() {
                alert( 'Couldn\'t POST data to that URL. Please try again.' );
            },
            501: function() {
                alert( 'You don\'t own that offer. Not sending POST data.' );
            }
        }
    });
};

function maybeShowIntervalField() {
    var type = document.getElementById( "type_dropdown" ).value;

    if( type == "subscription" ) {
        disp = "table-row";
    } else {
        disp = "none";
    }
    document.getElementById( "interval_row" ).style.display = disp;
};

