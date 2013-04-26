var GUID_SYNTAXES = {
    "hash": "GUID = hash of record information",
    "filename": "GUID = \"{GUID Prefix}{File Name}\"",
    "fullpath": "GUID = \"{GUID Prefix}{Full Path}\""
}

initCSVGenUI = function() {
    initGUIDSyntaxSelector();

    // Set up csv-generation-form
    $('#csv-generation-form').validate({
        onfocusout: false,
        onkeyup: false,
        onsubmit: false,
        errorPlacement: function(error, element) {},
        highlight: function(element) {
            $(element).closest('.control-group').addClass('error');
        },
        unhighlight: function(element) {
            $(element).closest('.control-group').removeClass('error');
        },
        rules: {
            gimagedir: {
                required: true
            }
        }
    });
    
    $('#csv-generation-form').submit(function(event) {
        event.preventDefault();
        if ($('#csv-generation-form').valid()) {
            var values = 
                "{\'g-imagedir\':\'" + processFieldValue('#gimagedir') +
                "\',\'g-recursive\':\'" + $('#g-recursive-cb').is(":checked") +
                "\',\'g-guidsyntax\':\'" + processFieldValue('#g-guidsyntax-dropdown') +
                "\',\'g-guidprefix\':\'" + processFieldValue('#g-guidprefix') +
                "\',\'g-save-path\':\'" + processFieldValue('#g-save-path') +
                "\',\'g-desc\':\'" + processFieldValue('#g-desc') +
                "\',\'g-lang\':\'" + processFieldValue('#g-lang') +
                "\',\'g-title\':\'" + processFieldValue('#g-title') +
                "\',\'g-digdev\':\'" + processFieldValue('#g-digdev') +
                "\',\'g-pixres\':\'" + processFieldValue('#g-pixres') +
                "\',\'g-mag\':\'" + processFieldValue('#g-mag') +
                "\',\'g-ocr-output\':\'" + processFieldValue('#g-ocr-output') +
                "\',\'g-ocr-tech\':\'" + processFieldValue('#g-ocr-tech') +
                "\',\'g-info-wh\':\'" + processFieldValue('#g-info-wh') +
                "\',\'g-col-obj-guid\':\'" + processFieldValue('#g-col-obj-guid') +
                "\'}";
            
            postCsvGeneration(values);
        }
        else {
            showAlert2('Error: The upload directory cannot be empty.', "", "");
        }
    })
    
    $('#g-flip-opt-fields').click(function(event) {
        if ($('#g-opt-fields').hasClass("hide")) {
            $('#g-opt-fields').removeClass("hide");
            $('#g-filp-opt-fields-text').text("Hide Other Fields");
        }
        else {
            $('#g-opt-fields').addClass("hide");
            $('#g-filp-opt-fields-text').text("Show Other Fields");
        }
    });
}

initGUIDSyntaxSelector = function() {
    $.each(GUID_SYNTAXES, function(key, value) {
        var option = ["<option value=\"", key, "\">", value, "</option>"].join("");
        $("#g-guidsyntax-dropdown").append(option);
    });
    $("#g-guidsyntax-dropdown option[value='']").remove();
    
    $("#g-guidsyntax-dropdown").change(function(e) {
        var syntaxName = $("#g-guidsyntax-dropdown").val();
//        setPreference('g-guidsyntax', syntaxName);
        if (syntaxName == "hash") {
            if (! $('#g-guidprefix-group').hasClass("hide")) {
                $("#g-guidprefix-group").addClass('hide');
            }
        }
        else {
            if ($('#g-guidprefix-group').hasClass("hide")) {
                $('#g-guidprefix-group').removeClass("hide");
            }
        }
    });
}

postCsvGeneration = function(values) {
    // Reset the elements
    $("#progressbar-container-csvgen").removeClass('in');
    $("#progressbar-container-csvgen").removeClass('hide');
    
    var callback = function(targetpath){
        // Disable inputs
        $('#gimagedir').attr('disabled', true);
        $("#gimagedir").addClass('disabled');

        $("#g-recursive-cb").attr('disabled', true);
        $("#g-recursive-cb").addClass('disabled');

        $('#g-guidsyntax-dropdown').attr('disabled', true);
        $("#g-guidsyntax-dropdown").addClass('disabled');

        $('#g-guidprefix').attr('disabled', true);
        $("#g-guidprefix").addClass('disabled');
        
        $('#g-save-path').attr('disabled', true);
        $("#g-save-path").addClass('disabled');

        $('#g-desc').attr('disabled', true);
        $("#g-desc").addClass('disabled');

        $('#g-lang').attr('disabled', true);
        $("#g-lang").addClass('disabled');

        $('#g-title').attr('disabled', true);
        $("#g-title").addClass('disabled');

        $('#g-digdev').attr('disabled', true);
        $("#g-digdev").addClass('disabled');

        $("#g-pixres").attr('disabled', true);
        $("#g-pixres").addClass('disabled');
        
        $("#g-mag").attr('disabled', true);
        $("#g-mag").addClass('disabled');

        $("#g-ocr-output").attr('disabled', true);
        $("#g-ocr-output").addClass('disabled');

        $("#g-ocr-tech").attr('disabled', true);
        $("#g-ocr-tech").addClass('disabled');

        $("#g-info-wh").attr('disabled', true);
        $("#g-info-wh").addClass('disabled');

        $("#g-col-obj-guid").attr('disabled', true);
        $("#g-col-obj-guid").addClass('disabled');

        $("#csv-generate-button").attr('disabled', true);
        $("#csv-generate-button").addClass('disabled');
        
        // Show progress bar in animation
        $(".progress-primary").addClass('active');
        $("#progressbar-container-csvgen").addClass('in');

        setTimeout("updateCSVGenProgress()", 100);
    };
    
    // now send the form and wait to hear back
    $.post("/services/generatecsv", { values: values }, callback, 'json');
}

updateCSVGenProgress = function() {
    var url = '/services/csvgenprogress';
    
    $.getJSON(url, function(progressObj) {
        
        $("#progresstext2").text("Processed: " + progressObj.count + " files.");
        
        if (progressObj.result != 0) {
            $(".progress-primary").toggleClass('active');

            $('#gimagedir').attr('disabled', false);
            $("#gimagedir").removeClass('disabled');

            $("#g-recursive-cb").attr('disabled', false);
            $("#g-recursive-cb").removeClass('disabled');

            $('#g-guidsyntax-dropdown').attr('disabled', false);
            $("#g-guidsyntax-dropdown").removeClass('disabled');

            $('#g-guidprefix').attr('disabled', false);
            $("#g-guidprefix").removeClass('disabled');
            
            $('#g-save-path').attr('disabled', false);
            $("#g-save-path").removeClass('disabled');

            $('#g-desc').attr('disabled', false);
            $("#g-desc").removeClass('disabled');

            $('#g-lang').attr('disabled', false);
            $("#g-lang").removeClass('disabled');

            $('#g-title').attr('disabled', false);
            $("#g-title").removeClass('disabled');

            $('#g-digdev').attr('disabled', false);
            $("#g-digdev").removeClass('disabled');

            $("#g-pixres").attr('disabled', false);
            $("#g-pixres").removeClass('disabled');
            
            $("#g-mag").attr('disabled', false);
            $("#g-mag").removeClass('disabled');

            $("#g-ocr-output").attr('disabled', false);
            $("#g-ocr-output").removeClass('disabled');

            $("#g-ocr-tech").attr('disabled', false);
            $("#g-ocr-tech").removeClass('disabled');

            $("#g-info-wh").attr('disabled', false);
            $("#g-info-wh").removeClass('disabled');

            $("#g-col-obj-guid").attr('disabled', false);
            $("#g-col-obj-guid").removeClass('disabled');

            $("#csv-generate-button").attr('disabled', false);
            $("#csv-generate-button").removeClass('disabled');

            if (progressObj.result == 1) {
                targetfile = progressObj.targetfile.replace(/\\\\/g, "\\"); // Make sure the "\\" is replaced with "\".
                showAlert2("The CSV file is successfully saved to: " +
                    targetfile, "", "alert-success");
            } else {
                showAlert2("Error: " + progressObj.error, "", "alert-error");
            }
        } else { // Not finished.
            // Calls itself again after 100ms.
            setTimeout("updateCSVGenProgress()", 100);
        }
    });
}

/**
 * Display an alert message in the designated alert container.
 * @param {HTML string} message 
 * @param {HTML string} [additionalElement] Additional element(s) in the second row.
 * @param {String} [alertType] The alert type, i.e. Bootstrap class, default to 
 *   alert-error.
 */
showAlert2 = function(message, additionalElement, alertType) {
    additionalElement = additionalElement || "";
    alertType = alertType || "alert-error";
    container = "#alert-container-2";
    
    var alert_html =
        ['<div class="alert alert-block fade span10" id="upload-alert-2">',
        '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="alert-text-2">',
        '<div id="alert-extra-2">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#upload-alert-2").show();
    $("#upload-alert-2").addClass('in');
    $("#upload-alert-2").addClass(alertType);
    $("#alert-text-2").html(message);
    $("#alert-extra-2").html(additionalElement);
}
