initHistoryUI = function() {
    $('#refresh-bh-button').click(function(event) {
        $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
    });

    $('#history-tab-button').click(function(event) {
        $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);
    });

    $.getJSON('/services/history', { table_id: "" }, renderBatchHistory);

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
