/*  Make a form POST and receive JSON via AJAX.
    Options:
    
    beforeSubmit: function(form_dict)
        Modify a key-value dictionary representing form's data before submitting
    
    success: function(json)
        Receive server JSON
    
    error: function(json, text_status)
        Receive server error JSON (if possible) and the error status
*/
function jsonAjaxForm(form, options) {
    $(form).submit(function() {
        var form_dict = {};
        $.each(form.serializeArray(), function(key, value) {
            form_dict[value.name] = value.value;
        });
        
        options['beforeSubmit'](form_dict);
        
        var ajaxSubmitOptions = {
            url: $(form).attr('action'),
            dataType: 'json',
            type: 'post',
            data: { json: JSON.stringify(form_dict) },
            success: function(data, text_status, xhr) {
                // Call the success handler
                options['success'](JSON.parse(data));
            },
            error: function(xhr, text_status, error_thrown) {
                // Call the error handler
                options['error'](JSON.parse(xhr.responseText), text_status);
            }
        };
        
        // Update ajaxSubmitOptions with the passed-in options
        $.extend(ajaxSubmitOptions, options);
        $.ajax(ajaxSubmitOptions);
        
        return false;
    });
}
