$(document).ready(function() {
    getPreference('devmode_disable_startup_service_check', function(val) {
        if (val != 'true') {
            checkAuthentication();
        } else {
            $.unblockUI();
            initMainUI();
        }
    });
    
    // Certain UI components will be disabled if JS is. This overrides the css
    // that hides them (ingestion.ui.css), making sure they are shown.
    $(".js-required").not('.hidden').css("display", "inherit");
    if ($(".js-required").hasClass('hidden')) {
        $('#unsupported-browser-msg').show();
    }
});

var IMAGE_LICENSES = {
    "CC0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/"],
    "CC BY": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/3.0/"],
    "CC BY-SA": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/3.0/"],
    "CC BY-NC": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/3.0/"],
    "CC BY-NC-SA": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/3.0/"]
};

var GUID_SYNTAXES = {
    "filename": "GUID = \"{GUID Prefix}/{File Name}\"",
    "full-path": "GUID = \"{GUID Prefix}/{Full Path}\""
}

initMainUI = function() {
    showLastBatchInfo();
    initCsvUploadUI();

    $("body").tooltip({
        selector: '[rel=tooltip]'
    });

    $('#logout-btn').click(function(e) {
        $.ajax({
            url: "/services/config",
            type: 'DELETE'
        }).done(function() {
            location.reload();
        });
    });

    // Set up csv-upload-form
    $('#csv-upload-form').validate({
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
            imagelicense: {
                required: {
                    depends: function(element) {
                        return $("#imagelicense").val() != '';
                    }
                }
            },
            rsguid: {
                required: true
            },
            csvpath: {
                required: true
            }
        }
    });

    $('#csv-upload-form').submit(function(event) {
        event.preventDefault();
        if ($('#csv-upload-form').valid()) {
            setPreference('rsguid', $('#rsguid').val())
            setPreference('imagelicense', $('#csv-license-dropdown').val())
            setPreference('mediaContentKeyword', $('#mediaContentKeyword').val())
            setPreference('iDigbioProviderGUID', $('#csv-owneruuid').val())
            setPreference('iDigbioPublisherGUID', $('#iDigbioPublisherGUID').val())
            setPreference('fundingSource', $('#fundingSource').val())
            setPreference('fundingPurpose', $('#fundingPurpose').val())
            postCsvUpload("new");
        } else {
            showAlert('The Image License, Record Set GUID and CSV File Path cannot be empty.');
        }
    });

    $('#refresh-bh-button').click(function(event) {
        $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
    });

    $('#history-tab-button').click(function(event) {
        $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
    });

    $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
}

initCsvUploadUI = function() {
    initCsvLicenseSelector();
}

checkAuthentication = function() {
    blockUI();
    
    $.getJSON('/services/auth', function(data) {
        $.unblockUI();
        if (!data) {
            initLoginModal();
        } else {
            initMainUI();
        }
    })
    
    .error(function(data) {
        $.unblockUI();
        $('#serviceErrorModal').modal();
    });
}

blockUI = function() {
    var div = document.createElement("div");
    var throb = new Throbber({
        color: 'white',
        padding: 30,
        size: 100,
        fade: 200,
        clockwise: false
    }).appendTo(div).start();
    $.blockUI.defaults.css = {}; 
    $.blockUI({ 
        message: div
     });
}

initLoginModal = function() {
    $('#loginModal').modal();

    $('#login-form').validate({
        onkeyup: false,
        errorElement:'span',
        errorClass:'help-inline',
        highlight: function(element, errorClass, validClass) {
            $(element).closest('.control-group').addClass('error');
        },
        unhighlight: function (element, errorClass, validClass) { 
            $(element).parents(".error").removeClass('error');
        },
        rules: {
            accountuuid: {
                rangelength: [32, 36],
                required: true
            },
            apikey: {
                rangelength: [32, 36],
                required: true
            }
        }
    });
    
    $('#login-button').click(function(event) {
        event.preventDefault();
        if ($('#login-button').attr('disabled')) {
            return;
        }

        if (!$('#login-form').valid()) {
            return;
        }
        
        var accountuuid = $("#accountuuid").val();
        var apikey = $("#apikey").val();

        $('#login-button').attr('disabled', true);
        $('#login-button').addClass('disabled');
        new Throbber({
            color: '#005580',
            size: 20
        }).appendTo($('#login-error')[0]).start();

        $.post('/services/auth', { user: accountuuid, password: apikey }, function(data) {
            $('#login-form > .control-group').removeClass('error');
            $('#login-error').addClass('hide');

            $('#loginModal').modal('hide');
            initMainUI();
        }, 'json')
        .error(function(err) {
            if (err.status == 409) {
                $('#login-error').html('Wrong Account UUID and API Key combination..');
                $('#login-button').attr('disabled', false);
                $('#login-button').removeClass('disabled');
            } else {
                $('#login-error').html('Cannot sign in due to iDigBio service unavailable. Please come back later.');
            }
            $('#login-form > .control-group').addClass('error');
            $('#login-error').removeClass('hide');
        });
    });
}

initCsvLicenseSelector = function() {
    $.each(IMAGE_LICENSES, function(key, value) {
        var option = ["<option value=\"", key, "\">", value[0], " ", 
            value[1], "</option>"].join("");
        $("#csv-license-dropdown").append(option);
    });
    
    $("#csv-license-dropdown").change(function(e) {
        var licenseName = $("#csv-license-dropdown").val();
        var license = IMAGE_LICENSES[licenseName];
        showAlert(["The images will be uploaded under the terms of the ", 
                license[0], " ", license[1], " license (see <a href=\"", license[2], 
                "\" target=\"_blank\">definition</a>)."].join(""), 
            null, "alert-info");
        setPreference('imagelicense', licenseName);
    });
}

postCsvUpload = function(action) {
    // Reset the elements
    $("#result-table-container").removeClass('in');
    $("#result-table-container").removeClass('hide');
    $("#progressbar-container").removeClass('in');
    $("#progressbar-container").removeClass('hide');
    
    var callback = function(dataReceived){
        // Disable inputs
        $('#csv-license-dropdown').attr('disabled', true);
        $("#csv-license-dropdown").addClass('disabled');

        $('#rsguid').attr('disabled', true);
        $("#rsguid").addClass('disabled');

        $('#csv-path').attr('disabled', true);
        $("#csv-path").addClass('disabled');
        
        $('#mediaContentKeyword').attr('disabled', true);
        $("#mediaContentKeyword").addClass('disabled');

        $('#csv-owneruuid').attr('disabled', true);
        $("#csv-owneruuid").addClass('disabled');

        $('#iDigbioPublisherGUID').attr('disabled', true);
        $("#iDigbioPublisherGUID").addClass('disabled');

        $('#fundingSource').attr('disabled', true);
        $("#fundingSource").addClass('disabled');

        $('#fundingPurpose').attr('disabled', true);
        $("#fundingPurpose").addClass('disabled');

        $("#csv-upload-button").attr('disabled', true);
        $("#csv-upload-button").addClass('disabled');

//        $("#logout-btn").attr('disabled', true);
//        $("#logout-btn").addClass('disabled');
               
        // Clean up UI.
        $("#upload-alert").alert('close');
        
        // Show progress bar in animation
        $(".progress-primary").addClass('active');
        $("#progressbar-container").addClass('in');
        
        setTimeout("updateProgress()", 1000);
    };
    
    // now send the form and wait to hear back
    if (action == "new") {
        var csvPath = $('#csv-path').val();

        $.post('/services/csv', { csvPath: csvPath }, callback, 
                'json')
        .error(function(data) {
            var errMsg = "<strong>Error! </strong>" + data.responseText;
            showAlert(errMsg)
        });
    } else {
        $.post('/services/csv', callback, 'json')
        .error(function(data) {
            var errMsg = "<strong>Error! </strong>" + data.responseText;
            showAlert(errMsg);
        });
    }
}

showLastBatchInfo = function() {
    $.getJSON('/services/batch', function(batch) {
        if (batch.Empty) {
            return;
        }
            
        if (!batch.finished) {
            var start_time = batch.start_time;
            var errMsg = ["<p><strong>Warning!</strong> Your last upload from directory/CSV file ",
            batch.path, " which started at ", start_time,
            ' was not entirely successful.</p>'].join("");
            var extra = '<p><button id="retry-button" type="submit" class="btn btn-warning">Retry failed uploads</button></p>';
            showAlert(errMsg, extra, "alert-warning");
            $("#retry-button").click(function(event) {
                event.preventDefault();
                $("#upload-alert").alert('close');
                // TODO: Differentiate the CSV task or dir task.
                postCsvUpload("retry");
                // Note: retry will reload the batch information, and read the CSV file again.
            });
        }
    }, "json");
}

/**
 * Display an alert message in the designated alert container.
 * @param {HTML string} message 
 * @param {HTML string} [additionalElement] Additional element(s) in the second row.
 * @param {String} [alertType] The alert type, i.e. Bootstrap class, default to 
 *   alert-error.
 */
showAlert = function(message, additionalElement, alertType, container) {
    additionalElement = additionalElement || "";
    alertType = alertType || "alert-error";
    container = container || "#alert-container";
    
    var alert_html =
        ['<div class="alert alert-block fade span10" id="upload-alert">',
        '<button class="close" data-dismiss="alert">&times;</button>',
        '<p id="alert-text">',
        '<div id="alert-extra">',
        '</div>'].join('\n');
    $(container).html(alert_html);
    $("#upload-alert").show();
    $("#upload-alert").addClass('in');
    $("#upload-alert").addClass(alertType);
    $("#alert-text").html(message);
    $("#alert-extra").html(additionalElement);
}

updateProgress = function() {
    var url = '/services/progress';
    
    $.getJSON(url, function(progressObj) {
        
        var progress = progressObj.total == 0 ? 100 : 
            Math.floor((progressObj.successes + progressObj.fails + 
                progressObj.skips) / progressObj.total * 100);
        
        
        $("#progresstext").text(["Progress: (Successful:" + progressObj.successes,
             ", Skipped: " + progressObj.skips,
             ", Failed: " + progressObj.fails,
             ", Total to upload: " + progressObj.total,
             ")"].join(""));
        
        $("#upload-progressbar").width(progress + '%');
        
        if (progressObj.finished) {
            $(".progress-primary").toggleClass('active');

            $('#csv-license-dropdown').attr('disabled', false);
            $("#csv-license-dropdown").removeClass('disabled');

            $('#rsguid').attr('disabled', false);
            $("#rsguid").removeClass('disabled');

            $('#csv-path').attr('disabled', false);
            $("#csv-path").removeClass('disabled');
            
            $('#mediaContentKeyword').attr('disabled', false);
            $("#mediaContentKeyword").removeClass('disabled');

            $('#csv-owneruuid').attr('disabled', false);
            $("#csv-owneruuid").removeClass('disabled');

            $('#iDigbioPublisherGUID').attr('disabled', false);
            $("#iDigbioPublisherGUID").removeClass('disabled');

            $('#fundingSource').attr('disabled', false);
            $("#fundingSource").removeClass('disabled');

            $('#fundingPurpose').attr('disabled', false);
            $("#fundingPurpose").removeClass('disabled');

            $("#csv-upload-button").attr('disabled', false);
            $("#csv-upload-button").removeClass('disabled');


//            $("#logout-btn").attr('disabled', false);
//            $("#logout-btn").removeClass('disabled');
            
            if (progressObj.fails > 0 || progressObj.total == 0) {
                if (progressObj.fails > 0) {
                    var errMsg = ["<p><strong>Warning!</strong> ",
                        "This upload was not entirely successful. ",
                        "You can retry it at a later time."].join("");
                    if (progress < 100) {
                        errMsg += [' Upload aborted before all images are tried ', 
                            'due to continuing erroneous network conditions.'].join('');
                    }
                    var extra = ['<p><button id="retry-button" type="submit"',
                        'class="btn btn-warning">Retry failed uploads</button></p>'].join("");
                } else {
                    $.getJSON('/services/batch', function(batch) {
                        var errMsg = ["<p><strong>Warning!</strong> ",
                            batch.ErrorCode,
                            " Please fix it and retry the upload."].join("");
                        showAlert(errMsg, extra, "alert-warning");
                    });
                }
                $("#retry-button").click(function(event) {
                    event.preventDefault();
                    $("#upload-alert").alert('close');
                // TODO: Differentiate the CSV task or dir task.
                    postCsvUpload("retry");
                });
            }
            
            if (progressObj.total > 0) {
                // If we haven't tried one file, no need to get results.
                $.getJSON('/services/result', renderResult);
            }
            
            return;
        }
        
        // Calls itself again after 4000ms.
        setTimeout("updateProgress()", 4000);
    });
}

renderBatchHistory = function(data) {
    if ($('#batch-history-table-container').hasClass('hide')) {
        $('#batch-history-table-container').removeClass('hide');
        $('#batch-history-table-container').addClass('in');
    }

    var bht = $('#batch-history-table').dataTable({
        "aaData": data,
        "aoColumns": [
            { "sTitle": "ID", "sWidth": "5%" },
            { "sTitle": "CSVfilePath", "sWidth": "35%" },
            { "sTitle": "iDigbioProvidedByGUID", "bVisible": false },
            { "sTitle": "RightsLicense", "bVisible": false },
            { "sTitle": "RightsLicenseStatementUrl", "bVisible": false },
            { "sTitle": "RightsLicenseLogoUrl", "bVisible": false },
            { "sTitle": "RecordSetGUID", "sWidth": "12%" },
            { "sTitle": "RecordSetUUID", "bVisible": false },
            { "sTitle": "start_time", "sWidth": "15%" },
            { "sTitle": "finish_time", "sWidth": "15%" },
            { "sTitle": "MediaContentKeyword", "bVisible": false },
            { "sTitle": "iDigbioProviderGUID", "bVisible": false },
            { "sTitle": "iDigbioPublisherGUID", "bVisible": false },
            { "sTitle": "FundingSource", "bVisible": false },
            { "sTitle": "FundingPurpose", "bVisible": false },
            { "sTitle": "Records", "sWidth": "8%" }
        ],
        "sDom": "<'row'<'span5'l><'span6'p>>tr<'row'<'span6'i>>",
        "bPaginate": true,
        "bLengthChange": true,
        "bFilter": false,
        "bSort": true,
        "bInfo": true,
        "bAutoWidth": false,
        /*
        "oTableTools": {
            "sSwfPath": "assets/TableTools/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
            {
                "sExtends": "csv",
                "sButtonText": 'CSV(Complete)',
                "sFieldBoundary": '"',
                "sFieldSeperator": ',',
                "sFileName": 'iDigBio-batch-history.csv'
            },
            {
                "sExtends": 'pdf',
                "sTitle": 'iDigBio',
                "sButtonText": 'PDF(Selective)',
                "mColumns": "visible"
            }]
        },
        */
        "bDestroy" : true,
        "sPaginationType": "bootstrap"
    });
    
    // We do the row selection here outside datatable, 
    // because the dataTable is not doing well in supporting row selections.
    $('#batch-history-table').delegate('tbody > tr > td', 'click', function (event)
    {
        /*
        if ($(this.parentNode).hasClass('row_selected')) {
            $(this.parentNode).removeClass('success');
            $(this.parentNode).removeClass('row_selected');

            if ($('#image-history-table-container').hasClass('in')) {
                $('#image-history-table-container').removeClass('in');
                $('#image-history-table-container').addClass('hide');
            }
        }
        else {*/
            $(bht.fnSettings().aoData).each(function (){
                $(this.nTr).removeClass('success');
                $(this.nTr).removeClass('row_selected');
            });

            if (! $(this.parentNode).hasClass('row_selected')) {
                $(this.parentNode).addClass('success');
                $(this.parentNode).addClass('row_selected');
            }
            
            var aData = bht.fnGetData( this.parentNode );//get data of the clicked row

            $.getJSON('/services/history', { table_id: aData[0] }, renderMediaRecordHistory);
            $('#image-history-table-description').text("Batch ID: " + aData[0]);
        //}
    });
}

renderMediaRecordHistory = function(data) {
    if ($('#image-history-table-container').hasClass('hide')) {
        $('#image-history-table-container').removeClass('hide');
        $('#image-history-table-container').addClass('in');
    };
    $('#image-history-table').dataTable({
        "aaData": data,
        "aoColumns": [
            { "sTitle": "OriginalFileName", "sWidth": "42%" },
            { "sTitle": "MediaError", "bVisible": false },
            { "sTitle": "MediaGUID", "bVisible": false },
            { "sTitle": "MediaRecordUUID", "bVisible": false },
            { "sTitle": "MediaAccessUUID", "bVisible": false },
            { "sTitle": "Comments", "bVisible": false },
            { "sTitle": "UploadTime", "bVisible": false },
            { "sTitle": "MediaURL", "bVisible": false },
            { "sTitle": "Description", "bVisible": false },
            { "sTitle": "LanguageCode", "bVisible": false },
            { "sTitle": "Title", "bVisible": false },
            { "sTitle": "DigitalizationDevice", "bVisible": false },
            { "sTitle": "NominalPixelResolution", "bVisible": false },
            { "sTitle": "Magnification", "bVisible": false },
            { "sTitle": "OcrOutput", "bVisible": false },
            { "sTitle": "OcrTechnology", "bVisible": false },
            { "sTitle": "InformationWithheld", "bVisible": false },
            { "sTitle": "CollectionObjectGUID", "bVisible": false },
            { "sTitle": "MediaMD5", "bVisible": false },
            { "sTitle": "MimeType", "bVisible": false },
            { "sTitle": "MediaSizeInBytes", "bVisible": false },
            { "sTitle": "ProviderCreatedTimeStamp", "bVisible": false },
            { "sTitle": "providerCreatedByGUID", "bVisible": false },
            { "sTitle": "MediaRecordEtag", "bVisible": false },
            { "sTitle": "RecordSetUUID", "bVisible": false },
            { "sTitle": "iDigbioProvidedByGUID", "bVisible": false },
            { "sTitle": "MediaContentKeyword", "bVisible": false },
            { "sTitle": "FundingSource", "bVisible": false },
            { "sTitle": "FundingPurpose", "bVisible": false },
            { "sTitle": "iDigbioPublisherGUID", "bVisible": false },
            { "sTitle": "RightsLicenseStatementUrl", "bVisible": false },
            { "sTitle": "RightsLicenseLogoUrl", "bVisible": false },
            { "sTitle": "iDigbioProviderGUID", "bVisible": false },
            { "sTitle": "RightsLicense", "bVisible": false },
            { "sTitle": "CSVfilePath", "bVisible": false },
            { "sTitle": "RecordSetGUID", "bVisible": false },
            {
                "sTitle": "Online Path or Error Message",
                "sWidth": "58%",
                "fnRender": function(obj) {
                    file_error = obj.aData[1]; // It is given as an array.
                    url = obj.aData[7];
                    var text;
                    if (file_error != null) {
                        text = "<span class=\"label label-important\">" + file_error + "</span>"
                    } else if (url == null) {
                        text = "<span class=\"label label-important\">This image is not successfully uploaded.</span>"
                    } else {
                        text = '<a target="_blank" href="' + url + '">'+ url + '</a>';
                    }
                    return text;
                }
            } // 33 elements.
        ],
        "sDom": "<'row'<'span3'l><'span3'T><'span5'p>>t<'row'<'span6'i>>",
        "bPaginate": true,
        "bLengthChange": true,
        "bFilter": false,
        "bSort": true,
        "bInfo": true,
        "bAutoWidth": false,
        "oTableTools": {
            "sSwfPath": "assets/TableTools/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
            {
                "sExtends": "csv",
                "sButtonText": 'CSV(Complete)',
                "sFieldBoundary": '"',
                "sFieldSeperator": ',',
                "sFileName": 'iDigBio-history.csv'
            },
            {
                "sExtends": 'pdf',
                "sTitle": 'iDigBio-history',
                "sButtonText": 'PDF(Selective)',
                "mColumns": "visible"
            }]
        },
        "bDestroy" : true,
        "sPaginationType": "bootstrap"
    });
}

renderResult = function(data) {
    $('#result-table-container').addClass('in');
    $('#result-table').dataTable({
        "aaData": data,
        "aoColumns": [
            { "sTitle": "OriginalFileName", "sWidth": "42%" },
            { "sTitle": "MediaError", "bVisible": false },
            { "sTitle": "MediaGUID", "bVisible": false },
            { "sTitle": "MediaRecordUUID", "bVisible": false },
            { "sTitle": "MediaAccessUUID", "bVisible": false },
            { "sTitle": "Comments", "bVisible": false },
            { "sTitle": "UploadTime", "bVisible": false },
            { "sTitle": "MediaURL", "bVisible": false },
            { "sTitle": "Description", "bVisible": false },
            { "sTitle": "LanguageCode", "bVisible": false },
            { "sTitle": "Title", "bVisible": false },
            { "sTitle": "DigitalizationDevice", "bVisible": false },
            { "sTitle": "NominalPixelResolution", "bVisible": false },
            { "sTitle": "Magnification", "bVisible": false },
            { "sTitle": "OcrOutput", "bVisible": false },
            { "sTitle": "OcrTechnology", "bVisible": false },
            { "sTitle": "InformationWithheld", "bVisible": false },
            { "sTitle": "CollectionObjectGUID", "bVisible": false },
            { "sTitle": "MediaMD5", "bVisible": false },
            { "sTitle": "MimeType", "bVisible": false },
            { "sTitle": "MediaSizeInBytes", "bVisible": false },
            { "sTitle": "ProviderCreatedTimeStamp", "bVisible": false },
            { "sTitle": "providerCreatedByGUID", "bVisible": false },
            { "sTitle": "MediaRecordEtag", "bVisible": false },
            { "sTitle": "RecordSetUUID", "bVisible": false },
            { "sTitle": "iDigbioProvidedByGUID", "bVisible": false },
            { "sTitle": "MediaContentKeyword", "bVisible": false },
            { "sTitle": "FundingSource", "bVisible": false },
            { "sTitle": "FundingPurpose", "bVisible": false },
            { "sTitle": "iDigbioPublisherGUID", "bVisible": false },
            { "sTitle": "RightsLicenseStatementUrl", "bVisible": false },
            { "sTitle": "RightsLicenseLogoUrl", "bVisible": false },
            { "sTitle": "iDigbioProviderGUID", "bVisible": false },
            { "sTitle": "RightsLicense", "bVisible": false },
            { "sTitle": "CSVfilePath", "bVisible": false },
            { "sTitle": "RecordSetGUID", "bVisible": false },
            {
                "sTitle": "Online Path or Error Message",
                "sWidth": "58%",
                "fnRender": function(obj) {
                    file_error = obj.aData[1]; // It is given as an array.
                    url = obj.aData[7];
                    var text;
                    if (file_error != null) {
                        text = "<span class=\"label label-important\">" + file_error + "</span>"
                    } else if (url == null) {
                        text = "<span class=\"label label-important\">This image is not successfully uploaded.</span>"
                    } else {
                        text = '<a target="_blank" href="' + url + '">'+ url + '</a>';
                    }
                    return text;
                }
            } // 33 elements.
        ],
        "sDom": "<'row'<'span3'l><'span3'T><'span5'p>>t<'row'<'span6'i>>",
        "bPaginate": true,
        "bLengthChange": true,
        "bFilter": false,
        "bSort": true,
        "bInfo": true,
        "bAutoWidth": false,
        "oTableTools": {
            "sSwfPath": "assets/TableTools/swf/copy_csv_xls_pdf.swf",
            "aButtons": [
            {
                "sExtends": "csv",
                "sButtonText": 'CSV(Complete)',
                "sFieldBoundary": '"',
                "sFieldSeperator": ',',
                "sFileName": 'iDigBio-result.csv'
            },
            {
                "sExtends": 'pdf',
                "sTitle": 'iDigBio-result',
                "sButtonText": 'PDF(Selective)',
                "mColumns": "visible"
            }]
        },
        "bDestroy" : true,
        "sPaginationType": "bootstrap"
    });
}

getPreference = function(name, callback) {
    $.getJSON('/services/config', { name: name }, function(data) {
        callback(data);
    })
    .error(function(data) {
        callback(null);
    });
}

setPreference = function(name, val) {
    $.post('/services/config', { name: name, value: val }, function() { }, 'json');
}
