var campname = $("#campname").val();
var pno = $("#tonumber").val();
var message = $("#msg").val();
var uimgs = [];
var uvideo = "";
var updf = "";
var uaudio = "";


var imagespond = FilePond.create(document.getElementById("attimg1"),
    {
        instantUpload: true,
        maxFileSize: '1024KB',
        allowRevert: false,
        allowPaste: false,

        acceptedFileTypes: ['image/png', 'image/jpeg'],
        maxFiles: 4,
        labelIdle: 'Drag & Drop image files(maximum 4)or<br/> <span class="filepond--label-action"> Browse  Image</span>',
        server: {
            url: 'wapp/upload/media',
            process: {
                onload: function (fd) {
                    // alert(fd);
                    /*$("#message").val($("#message").val() + fd);*/

                    uimgs.push(fd);
                }
            }
        }
    }
);


var videopond = FilePond.create(document.getElementById("attvideo"),
    {
        instantUpload: true,
        allowRevert: false,
        allowPaste: false,
        maxFileSize: '3MB',
        acceptedFileTypes: ['video/mp4', 'video/3gpp', 'video/x-msvideo'],
        labelIdle: 'Drag & Drop Video files(max size:3 MB) or <span class="filepond--label-action"> Browse Video </span>',
        server: {
            url: 'wapp/upload/media',
            process: {
                onload: function (fd) {

                    $("#message").val($("#message").val() + fd);

                    uvideo = fd;
                }
            }
        }
    }
);


var pdfpond = FilePond.create(document.getElementById("attpdf"),
    {
        instantUpload: true,
        allowRevert: false,
        allowPaste: false,
        maxFileSize: '2MB',
        acceptedFileTypes: ['application/pdf'],
        labelIdle: 'Drag & Drop PDF file(max size:1 MB) or <span class="filepond--label-action"> Browse PDF </span>',
        server: {
            url: 'wapp/upload/media',
            process: {
                onload: function (fd) {

                    $("#message").val($("#message").val() + fd);
                    updf = fd;
                }
            }
        }
    }
);


var audiopond = FilePond.create(document.getElementById("attaudio"),
    {
        instantUpload: true,
        allowPaste: false,
        acceptedFileTypes: ['audio/wav'],
        labelIdle: 'Drag & Drop Audio file(max size:2 MB) or <span class="filepond--label-action"> Browse Audio </span>',
        server: {
            url: 'wapp/upload/media',
            process: {
                onload: function (fd) {

                    $("#message").val($("#message").val() + fd);
                    uaudio = fd;
                }
            }
        }
    }
);

function saveWhatsapp() {
    pno = $("#tonumber").val();
    campname = $("#campname").val();

    if (campname == "") {


        Swal.fire('Please enter the campaign name.',
            'error'
        );
    } else if (pno.length == 0) {
        Swal.fire('Please enter the phone number.',
            'error'
        );

    } else if ($("#msg").val().length > 2000) {

        Swal.fire('You have entered ' + $("#msg").val().length + ' characters. Please enter less than 2000 characters.',
            'error'
        );
    } else if (pno.length != 0) {

        $.ajax({
            method: "POST",
            url: "/wapp/campaign/save",
            data: {
                "campname": campname,
                "mobile": pno,
                "msg": $("#msg").val(),
                "imgs": uimgs,
                "video": uvideo,
                "pdf": updf,
                "audio": uaudio
            },
            beforeSend: function (c) {
                //   $.blockUI();
                $("#btnsndnow").attr("disabled", true);
            },
        }).done(function (msg) {
            //$.unblockUI();
            // alert(msg);
            $("#btnsndnow").attr("disabled", false);
            if (msg.statuscode == 200) {
                Swal.fire("Campaign submitted successfully. #" + msg.requestid);

                var urls = 'views/wapp.jsp';
                $("#ui-view").load(urls);


            } else if (msg.statuscode == 400 || msg.statuscode == 300) {

                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: msg.errormsg,
                    footer: 'Kindly Recharge. Contact your account manager'
                })

            } else {

            }
            /* if (msg.statuscode == 200) {
                 swal('SUCCESS..', msg.errormsg, 'success').then(function () {
                     location.reload(true);
                 });
             }
             else {
                 swal('ERROR..', msg.errormsg, 'error').then(function () {
                     location.reload(true);
                 });
             }*/

        });
    } else {

        swal('OOPS..', msg.errormsg, 'error');
    }

}

$(document).ready(function () {
    $("#tonumber").change(function () {
        getpnos(pno);
    });

});


function getpnos(pnos) {


    /*var no=pnos.split(',');*/
    var stringToClean = jQuery.trim($("#tonumber").val());

    if (stringToClean.length < 1) {

        return (false);
    }
    stringToClean = stringToClean.replace(/['"]+/g, '');
    stringToClean = stringToClean.replace(/[,]{2,}/g, ',').replace(/[/]{1,}/g, ',')
        .replace(/%/g, '').replace(/\+/g, '').replace(/_/g, '')
        .replace(/\r\n|\s|\n|\r/g, ",");
    var tempArr = stringToClean.split(',');

    var uniqueArray = new Array();
    var tot = tempArr.length;

    var dup = 0;

    for (var i = 0; i < tempArr.length; i++) {

        if (tempArr[i] == '') {
            tempArr.splice(i, 1);
            i--;
        } else if (isPhone(tempArr[i])) {

            if (tempArr[i].length == 12 && tempArr[i].startsWith("91")) {
                tempArr[i] = tempArr[i].substr(2);
            } else if (tempArr[i].length == 13 && tempArr[i].startsWith("+91")) {
                tempArr[i] = tempArr[i].substr(3);
            } else if (tempArr[i].length == 11 && tempArr[i].startsWith("0")) {
                tempArr[i] = tempArr[i].substr(1);
            }
            if (uniqueArray[tempArr[i]] != undefined) {
                tempArr.splice(i, 1);
                i--;
                dup++;
            }


        } else {
            tempArr.splice(i, 1);
            i--;
        }

        uniqueArray[tempArr[i]] = '';

    }

    var valid = tempArr.length;

    $("#tonumber").val(tempArr.join(','))

    $("#totalpno")
        .html(
            '<button  type="button" class="btn btn-primary  btn-xs">Total Valid Mobile:<b>'
            + valid
            + '</b></button><button  type="button" class="btn btn-warning  btn-xs">Duplicate:<b>'
            + dup
            + '</b></button><button  type="button" class="btn btn-danger  btn-xs">Invalid:<b>'
            + (tot - valid - dup) + "</b></buttton>");

}

function isPhone(p) {
    var regex = /^[0-9]{10,13}$/;
    /* [+{1}][0-9]{13} | [0-9]{10,11,12}*/
    return regex.test(p);

}
