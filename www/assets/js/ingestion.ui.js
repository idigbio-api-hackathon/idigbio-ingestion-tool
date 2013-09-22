$(document).ready(function() {
  checkAuthentication();
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

initMainUI = function() {
  showLastBatchInfo();
  initCsvLicenseSelector();

  $("body").tooltip({
    selector: '[rel=tooltip]'
  });

  $.getJSON('/services/config', { name: "accountuuid"}, function(data) {
    $('#account-uuid-text').text('Account UUID: ' + data);
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
      var values =
        "{\'CSVfilePath\':\'" + processFieldValue('#csv-path') +
        "\',\'RecordSetGUID\':\'" + processFieldValue('#rsguid') +
        "\',\'RightsLicense\':\'" + processFieldValue('#csv-license-dropdown') +
        "\',\'MediaContentKeyword\':\'" +
        processFieldValue('#mediaContentKeyword') +
        "\',\'iDigbioProviderGUID\':\'" +
        processFieldValue('#iDigbioProviderGUID') +
        "\',\'iDigbioPublisherGUID\':\'" +
        processFieldValue('#iDigbioPublisherGUID') +
        "\',\'fundingSource\':\'" + processFieldValue('#fundingSource') +
        "\',\'fundingPurpose\':\'" + processFieldValue('#fundingPurpose') +
        "\'}";
      postCsvUpload("new", values);
    }
    else {
      showAlert('The Image License, Record Set GUID and CSV File Path cannot be'
          +' empty.');
    }
    $("#upload-alert").hide();
  });

  initHistoryUI();
  initCSVGenUI();
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

    $.post('/services/auth', { accountuuid: accountuuid, apikey: apikey },
      function(data) {
      $('#login-form > .control-group').removeClass('error');
      $('#login-error').addClass('hide');
      $('#loginModal').modal('hide');
      initMainUI();
    }, 'json')
    .error(function(err) {
      if (err.status == 409) {
        $('#login-error').html(
          'Incorrect Account UUID and API Key combination..');
        $('#login-button').attr('disabled', false);
        $('#login-button').removeClass('disabled');
      } else {
        $('#login-error').html(
          'Cannot sign in due to iDigBio service unavailable. ' +
          'Please come back later.');
      }
      $('#login-form > .control-group').addClass('error');
      $('#login-error').removeClass('hide');
      $('#login-button').attr('disabled', false);
      $('#login-button').removeClass('disabled');
    });
  });
}

initCsvLicenseSelector = function() {
  $.each(IMAGE_LICENSES, function(key, value) {
    var option = ["<option value=\"", key, "\">", value[0], " ",
      value[1], "</option>"].join("");
    $("#csv-license-dropdown").append(option);
  });
  $("#csv-license-dropdown option[value='']").remove();

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

postCsvUpload = function(action, values) {
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

    $('#iDigbioProviderGUID').attr('disabled', true);
    $("#iDigbioProviderGUID").addClass('disabled');

    $('#iDigbioPublisherGUID').attr('disabled', true);
    $("#iDigbioPublisherGUID").addClass('disabled');

    $('#fundingSource').attr('disabled', true);
    $("#fundingSource").addClass('disabled');

    $('#fundingPurpose').attr('disabled', true);
    $("#fundingPurpose").addClass('disabled');

    $("#csv-upload-button").attr('disabled', true);
    $("#csv-upload-button").addClass('disabled');

    // Clean up UI.
//    $("#upload-alert").alert('close');

    // Show progress bar in animation
    $(".progress-primary").addClass('active');
    $("#progressbar-container").addClass('in');

    setTimeout("updateProgress()", 1000);
  };

  // now send the form and wait to hear back
  if (action == "new") {
    $.post('/services/ingest', { values: values }, callback, 'json')
    .error(function(data) {
      var errMsg = "<strong>Error! </strong>" + data.responseText;
      showAlert(errMsg)
    });
  } else {
    $.post('/services/ingest', callback, 'json')
    .error(function(data) {
      var errMsg = "<strong>Error! </strong>" + data.responseText;
      showAlert(errMsg);
    });
  }
}

showLastBatchInfo = function() {
  $.getJSON('/services/lastbatchinfo', function(batch) {
    if (batch.Empty) {
      return;
    }

    if (!batch.finished) {
      var start_time = batch.start_time;
      var errMsg = ['<p><strong>Warning!</strong> '
        + 'Your last upload from directory/CSV file ',
      batch.path, ' which started at ', start_time,
      ' was not entirely successful.</p>'].join("");
      var extra = '<p><button id="retry-button" type="submit"'
        + ' class="btn btn-warning">Retry failed uploads</button></p>';
      showAlert(errMsg, extra, "alert-warning");
      $("#retry-button").click(function(event) {
        event.preventDefault();
        $("#upload-alert").alert('close');
        // TODO: Differentiate the CSV task or dir task.
        postCsvUpload("retry");
        // Note: retry will reload the batch information, and read the CSV file
        // again.
      });
    }
  }, "json");
}

/**
 * Display an alert message in the designated alert container.
 * Param:
 *   {HTML string} message
 *   {HTML string} [additionalElement] Additional element(s) in the second row.
 *   {String} [alertType] The alert type, i.e. Bootstrap class, default to
 *   alert-error.
 */
showAlert = function(message, additionalElement, alertType) {
  additionalElement = additionalElement || "";
  alertType = alertType || "alert-error";
  container = "#alert-container";

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
  // dummy query string is added not to allow IE retrieve results
  // from its browser cache.
  // added by Kyuho in July 23rd 2013
  var url = '/services/ingestionprogress?&now=' + $.now();

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


		if (progressObj.fatal_server_error) {
			var errMsg = ["<p><strong>Warning!</strong> ",
						"<p>FATAL SERVER ERROR</p> ",
						"<p>Server under maintenance. Try Later</p>", ].join("");
			showAlert(errMsg, extra, "alert-warning");
		} else if (progressObj.input_csv_error) {
			var errMsg = ["<p><strong>O.o Input CSV FILE ERROR</strong> ",
						"<p>Your input CSV file is weird</p> ",
						"<p>THis error occurs when your CSV file has different number of columns among rows or any field contains double quatation mark(\")</p>", ].join("");
			showAlert(errMsg, extra, "alert-warning");

    } else if (progressObj.finished) {
      $(".progress-primary").toggleClass('active');

      $('#csv-license-dropdown').attr('disabled', false);
      $("#csv-license-dropdown").removeClass('disabled');

      $('#rsguid').attr('disabled', false);
      $("#rsguid").removeClass('disabled');

      $('#csv-path').attr('disabled', false);
      $("#csv-path").removeClass('disabled');

      $('#mediaContentKeyword').attr('disabled', false);
      $("#mediaContentKeyword").removeClass('disabled');

      $('#iDigbioProviderGUID').attr('disabled', false);
      $("#iDigbioProviderGUID").removeClass('disabled');

      $('#iDigbioPublisherGUID').attr('disabled', false);
      $("#iDigbioPublisherGUID").removeClass('disabled');

      $('#fundingSource').attr('disabled', false);
      $("#fundingSource").removeClass('disabled');

      $('#fundingPurpose').attr('disabled', false);
      $("#fundingPurpose").removeClass('disabled');

      $("#csv-upload-button").attr('disabled', false);
      $("#csv-upload-button").removeClass('disabled');

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

          var errMsg = ["<p><strong>Warning!</strong> ",
            "Nothing is uploaded. Maybe the CSV is empty or the network is down? ",
            "Please check the folder and network connection and ",
            "retry it by clicking the 'Upload' button."].join("");

        }
        showAlert(errMsg, extra, "alert-warning");
        $("#retry-button").click(function(event) {
          event.preventDefault();
          $("#upload-alert").alert('close');
        // TODO: Differentiate the CSV task or dir task.
          postCsvUpload("retry");
        });
      }

      if(progressObj.fails == 0 && progressObj.total > 0 ) {
        showAlert("All images are successfully uploaded!", "", "alert-success");
      }

      if (progressObj.total > 0) {
        // If we haven't tried one file, no need to get results.
        $.getJSON('/services/ingestionresult', renderResult);
      }

      return;
    }

    // Calls itself again after 1000ms.
    setTimeout("updateProgress ()", 1000);
  });
}

renderResult = function(data) {
  $('#result-table-container').addClass('in');
  $('#result-table').dataTable({
    "aaData": data,
    "aoColumns": [
      { "sTitle": "OriginalFileName", "sWidth": "42%" },
      { "sTitle": "MediaGUID", "bVisible": false },
      { "sTitle": "Error", "bVisible": false },
      { "sTitle": "Warnings", "bVisible": false },
      { "sTitle": "MediaRecordUUID", "bVisible": false },
      { "sTitle": "MediaAPUUID", "bVisible": false },
      { "sTitle": "UploadTime", "bVisible": false },
      { "sTitle": "MediaURL", "bVisible": false },
      { "sTitle": "MimeType", "bVisible": false },
      { "sTitle": "MediaSizeInBytes", "bVisible": false },
      { "sTitle": "ProviderCreatedTimeStamp", "bVisible": false },
      { "sTitle": "providerCreatedByGUID", "bVisible": false },
      { "sTitle": "MediaEXIF", "bVisible": false },
      { "sTitle": "Annotations", "bVisible": false },
      { "sTitle": "MediaRecordEtag", "bVisible": false },
      { "sTitle": "MediaMD5", "bVisible": false },
      { "sTitle": "CSVfilePath", "bVisible": false },
      { "sTitle": "iDigbioProvidedByGUID", "bVisible": false },
      { "sTitle": "RightsLicense", "bVisible": false },
      { "sTitle": "RightsLicenseStatementUrl", "bVisible": false },
      { "sTitle": "RightsLicenseLogoUrl", "bVisible": false },
      { "sTitle": "RecordSetGUID", "bVisible": false },
      { "sTitle": "RecordSetUUID", "bVisible": false },
      { "sTitle": "MediaContentKeyword", "bVisible": false },
      { "sTitle": "iDigbioProviderGUID", "bVisible": false },
      { "sTitle": "iDigbioPublisherGUID", "bVisible": false },
      { "sTitle": "FundingSource", "bVisible": false },
      { "sTitle": "FundingPurpose", "bVisible": false },
      {
        "sTitle": "Online Path or Error Message",
        "sWidth": "58%",
        "fnRender": function(obj) {
          error = obj.aData[2]; // It is given as an array.
          url = obj.aData[7];
          var text;
          if (error != "") {
            text = "<span class=\"label label-important\">" + error + "</span>"
          } else if (url == null) {
            text = "<span class=\"label label-important\">This image is not successfully uploaded.</span>"
          } else {
            text = '<a target="_blank" href="' + url + '">'+ url + '</a>';
          }
          return text;
        }
      } // 29 elements.
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

// Process the special values like \, ', ". Note that " is replaced with '.
processFieldValue = function(name) {
  return $(name).val().replace(/\\/g,"\\\\").replace(/'/g,"\\'").replace(/"/g,"\\'")
}
