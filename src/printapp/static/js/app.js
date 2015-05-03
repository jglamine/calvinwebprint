/*
This is an Ember app. See http://emberjs.com/ for documentation.

As only the root url route is used, most of the logic takes place in a single
controller.
*/

function logout_user() {
   var form = document.createElement('form');
   document.body.appendChild(form);
   form.method = 'POST';
   form.action = '/api/logout';
   form.submit();
}

window.App = Ember.Application.create({
  rootElement: '#ember'
});

// Main controller for the single page application.
//
// Data is loaded from a RESTful JSON api.
// If a valid session cookie exists, the following cookies will also be set:
//   'email' - The singed in user's email.
//   'isAuthenticated' - true if a valid session cookie is present.
App.ApplicationController = Ember.Controller.extend({
  init: function() {
    this._super();
    if (this.get('isAuthenticated')) {
      this.getQueueAndBudget();
    }
  },
  needs: 'queue',

  printBudget: null,
  loadingFailed: false,
  uniflowIsDown: false,
  email: $.cookie('email') || '',
  isAuthenticated: $.cookie('isAuthenticated') || false,

  isLoaded: function() {
    return this.get('printBudget') !== null;
  }.property('printBudget'),

  formattedPrintBudget: function() {
    return App.util.formatMoney(this.get('printBudget'));
  }.property('printBudget'),

  pagesEstimate: function() {
    return Math.round(this.get('printBudget') / 0.03);
  }.property('printBudget'),

  colorPagesEstimate: function() {
    return Math.round(this.get('printBudget') / 0.285);
  }.property('printBudget'),

  getQueueAndBudget: function() {
    var controller = this;
    $.get('/api/uniflowstatus')
    .done(function(data, textStatus, response) {
      controller.set('controllers.queue.model', data.queue);
      controller.set('printBudget', data.budget);
      controller.set('uniflowIsDown', false);
    })
    .error(function(data, textStatus, response) {
      controller.set('loadingFailed', true);
      if (data.status === 504) {
        controller.set('uniflowIsDown', true);
      } 
      else if (data.status === 401) {
        //The password in the session cookie is invalid, so sign the use out. 
        logout_user();
      } else {
        App.util.showAlert('#budgetError, #queueError');
        controller.set('uniflowIsDown', false);
      }
    });
  },

  actions: {

    // Sign out by posting to the logout api endpoint.
    // The browser will be redirected to the main page.
    signout: function() {
      logout_user();
    }

  }
});

App.SignInController = Ember.Controller.extend({
  needs: 'application',
  inputUsername: '',
  inputPassword: '',
  submitting: false,

  actions: {

    signin: function() {
      $('#signInError').hide();
      $('#signInErrorUniflowDown').hide();
      $('#invalidEmailError').hide();
      this.set('submitting', true);
      var username = $.trim(this.get('inputUsername')).toLowerCase();
      var password = this.get('inputPassword');

      if (username.indexOf('@') === -1) {
        username = username + '@students.calvin.edu';
      }

      var controller = this;
      if (!((username.indexOf('@students.calvin.edu') > -1) || (username.indexOf('@calvin.edu') > -1))) {
          App.util.showAlert('#invalidEmailError');
          controller.set('controllers.application.isAuthenticated', false);
          controller.set('inputPassword', '');
          controller.set('submitting', false);
          return;
      }
      
      $.post('/api/login', {
        email: username,
        password: password
      }).done(function(data, textStatus, response) {
        controller.set('controllers.application.email', username);
        controller.set('controllers.application.isAuthenticated', true);
        controller.get('controllers.application').getQueueAndBudget();
      }).error(function(data, textStatus, response) {
        controller.set('controllers.application.isAuthenticated', false);
        if (data.status === 504) {
          App.util.showAlert('#signInErrorUniflowDown');
        } else {
          App.util.showAlert('#signInError');
        }
      }).always(function(data, textStatus, response) {
        controller.set('inputPassword', '');
        controller.set('submitting', false);
      });
    }
  }
});

App.QueueController = Ember.ArrayController.extend({
  itemController: 'queueItem'
});

App.QueueItemController = Ember.ObjectController.extend({
  displayIsColor: function() {
    return this.get('color') ? 'Yes' : 'No';
  }.property('color'),

  displayPages: function() {
    return this.get('copies') * this.get('pages');
  }.property('copies', 'pages'),

  displayPrice: function() {
    return App.util.formatMoney(this.get('price'));
  }.property('price'),

  displayDate: function() {
    return moment(new Date(this.get('date'))).calendar();
  }.property('date')
});

App.CloudprintController = Ember.ObjectController.extend({
  init: function() {
    this._super();
    this.getCloudPrintStatus();
  },

  haveCloudPrintPermission: null,
  isPrinterInstalled: null,
  cloudPrintPermissionUrl: null,
  loadingError: false,

  addPrinterLink: 'http://www.calvin.edu/go/addcloudprint',
  showAddPrinterHelp: false,
  showAddPrinterButton: true,

  isLoaded: function() {
    return this.get('cloudPrintPermissionUrl') !== null;
  }.property('cloudPrintPermissionUrl'),

  getCloudPrintStatus: function() {
    var controller = this;
    return $.get('/api/cloudprintstatus')
    .done(function(data, textStatus, response) {
      controller.set('haveCloudPrintPermission', data.haveCloudPrintPermission);
      controller.set('isPrinterInstalled', data.isPrinterInstalled);
      controller.set('cloudPrintPermissionUrl', data.cloudPrintPermissionUrl);
    })
    .fail(function(data, textStatus, response) {
      controller.set('loadingError', true);
    });
  },

  checkIfPrinterAdded: function() {
    var controller = this;
    this.getCloudPrintStatus()
    .then(function() {
      controller.set('showAddPrinterHelp', true);
      controller.set('showAddPrinterButton', true);
    });
  },

  revokeCloudPrint: function() {
    var controller = this;
    $.post('/api/revokecloudprint')
    .done(function(data, textStatus, response) {
      controller.getCloudPrintStatus();
    });

  },

  actions: {

    onAddPrinter: function() {
      // open a url in a new window where users can add the Calvin printer
      // to their cloud print account.
      window.open(this.get('addPrinterLink', '_blank'));
      this.set('showAddPrinterButton', false);

      // when focus returns to this page, check if the printer was added
      var controller = this;
      window.addEventListener('focus', function(event) {
        controller.checkIfPrinterAdded();
        event.target.removeEventListener(event.type, arguments.callee);
      });
    },

    onContinue: function() {
      this.checkIfPrinterAdded();
    },

    onRevokeCloudPrint: function() {
      this.revokeCloudPrint();
    }
  }

});

App.PrintFormController = Ember.ObjectController.extend({
  needs: 'application',

  fileName: null,
  doubleSided: false,
  color: false,
  copies: 1,
  staple: false,
  collate: true,
  uploadProgress: 0.0,
  documentId: null,
  printing: false,
  showCollate: false,
  supportedFileTypes: ['txt', 'pdf', 'docx', 'doc', 'odt', 'xps', 'png', 'jpg', 'jpeg', 'gif'],
  
  inputSupportedFileTypes: function() {
    var fileTypes = this.get('supportedFileTypes');
    var result = '';
    for (var i = 0; i < fileTypes.length - 1; i++) {
      result += '.' + fileTypes[i] + ', ';
    };
    result += '.' + fileTypes[fileTypes.length - 1];
    return result;
  }.property('supportedFileTypes'),

  showCollate: function() {
    return this.get('copies') > 1;
  }.property('copies'),

  disableStaple: function() {
    if ( this.get('doubleSided') ) {
      $("label[for*='staple-checkbox']").css('cursor', 'default');
    } else {
      $("label[for*='staple-checkbox']").css('cursor', 'pointer');
    }
    return this.get('doubleSided');
  }.property('doubleSided'),

  disableDoubleSided: function() {
    if ( this.get('staple') ) {
      $("label[for*='double-sided-checkbox']").css('cursor', 'default');
    } else {
      $("label[for*='double-sided-checkbox']").css('cursor', 'pointer');
    }
    return this.get('staple');
  }.property('staple'),

  notReadyToSubmit: function() {
    return this.get('uploadProgress') != 1.0 || this.get('printing') === true;
  }.property('uploadProgress', 'printing'),

  fileSelected: function() {
    return this.get('fileName') === null;
  }.property('fileName'),

  uploadProgressBarWidth: function() {
    return 'width: ' + this.get('uploadProgress') * 100 + '%';
  }.property('uploadProgress'),

  actions: {
    selectFile: function() {
      $('#fileSizeError, #fileTypeError').hide();
      var element = document.getElementById('file-input');
      element.click();
    },

    handleFile: function() {
      var element = document.getElementById('file-input');
      var fileList = element.files;
      if (fileList.length === 0) {
        this.set('fileName', null);
        return;
      }

      var file = fileList[0];
      // limit to 100mb
      if (file.size > 100 * 1024 * 1024) {
        App.util.showAlert('#fileSizeError');
        return;
      }

      var extension = file.name.split('.').pop().toLowerCase();
      var supportedFileTypes = this.get('supportedFileTypes');
      if (supportedFileTypes.indexOf(extension) === -1) {
        App.util.showAlert('#fileTypeError');
        return;
      }

      this.set('uploadProgress', 0.0);
      this.set('fileName', file.name);

      var controller = this;

      this.uploadFile(file)
      .done(function(data, textStatus, response) {
        controller.set('uploadProgress', 1.0);
        controller.set('documentId', data.file_id);
      })
      .fail(function(data, textStatus, response) {
        controller.send('cancelUpload');
      });
    },

    submit: function() {
      $('#printSuccess, #printError').hide();
      this.set('printing', true);
      var controller = this;

      $.post('/api/print', {
        file_id: controller.get('documentId'),
        color: controller.get('color'),
        double_sided: controller.get('doubleSided'),
        staple: controller.get('staple'),
        collate: controller.get('collate'),
        copies: controller.get('copies')
      })
      .done(function(data, textStatus, response) {
        App.util.showAlert('#printSuccess');
        controller.set('uploadProgress', 0.0);
        controller.set('fileName', null);
        controller.set('documentId', null);
        controller.get('controllers.application').getQueueAndBudget();
      })
      .fail(function(data, textStatus, response) {
        App.util.showAlert('#printError');
      })
      .always(function(data, textStatus, response) {
        controller.set('printing', false);
        controller.set('copies', 1);
        controller.clearFileInput();
      });
    },

    cancelUpload: function() {
      this.set('fileName', null);
      this.set('documentId', null);
      this.set('uploadProgress', 0.0);

      this.clearFileInput();
    }
  },

  clearFileInput: function() {
    var element = document.getElementById('file-input');
    element.value = '';
  },

  uploadFile: function(file) {
    // Upload a file and track progress.
    // Returns a jquery promise.
    // see http://stackoverflow.com/questions/166221/how-can-i-upload-files-asynchronously-with-jquery
    var controller = this;
    var formData = new FormData();
    formData.append('file', file, file.name);

    var promise = $.ajax({
      url: '/api/upload',
      type: 'POST',
      xhr: function() {
        var xhr = $.ajaxSettings.xhr();
        if (xhr.upload) {
            xhr.upload.addEventListener('progress',
              function(event) {
                if (event.lengthComputable) {
                  // round to two decimal places
                  var progress = Math.round(((event.loaded / event.total) + 0.00001) * 100) / 100;
                  controller.set('uploadProgress', progress);
                }
              }, false);
        }
        return xhr;
      },
      data: formData,
      // Tell JQuery not to process data or worry about content-type.
      cache: false,
      contentType: false,
      processData: false
    });
    return promise;
  }
});

App.PrintersController = Ember.ObjectController.extend({
  init: function() {
    this._super();
    this.loadPrinters();
  },
  needs: ['campusMap'],

  buildingGroups: [],
  selectedGroup: {},
  showPrivatePrinters: false,
  selectionChanged: true,
  isLoaded: false,
  errorLoading: false,

  // List of printers to display.
  printers: function() {
    var printers = this.get('selectedGroup').printers || [];
    var showPrivatePrinters = this.get('showPrivatePrinters');

    return _(printers)
      .filter(function(printer) {
        return printer.public || showPrivatePrinters;
      })
      .map(this.formatPrinter)
      .valueOf();

  }.property('selectedGroup', 'showPrivatePrinters'),

  // Update the map when a different building is selected from the drop down.
  onGroupChange: function() {
    this.selectionChanged = !this.selectionChanged;
    if (this.selectionChanged) {
      this.get('controllers.campusMap').select(this.get('selectedGroup'));
    }
  }.observes('selectedGroup'),

  // Update the drop down when a building on the map is selected.
  onActiveChange: function() {
    this.selectionChanged = !this.selectionChanged;
    if (this.get('controllers.campusMap.mapLoaded') && this.selectionChanged) {
      this.selectionChanged = true;
      this.select(this.get('controllers.campusMap.active'));
    }
  }.observes('controllers.campusMap.active'),

  select: function(group) {
    var group = _.find(this.get('buildingGroups'), function(buildingGroup) {
      return buildingGroup.id === group.id;
    });
    this.set('selectedGroup', group);
  },

  loadPrinters: function() {
    var controller = this;
    $.getJSON('static/printers.json')
    .done(function(data) {
      controller.set('buildingGroups', data.sort(function(a, b) {
        if (a.displayName < b.displayName) return -1;
        if (b.displayName < a.displayName) return 1;
        return 0;
      }));
      controller.set('selectedGroup', _.find(data, function(group) {
        return group.id === 'library';
      }));

      controller.get('controllers.campusMap').select(controller.get('selectedGroup'));
      controller.get('controllers.campusMap').set('printersLoaded', true);
      controller.get('controllers.campusMap').bindMapButtons();
      controller.set('isLoaded', true);
    })
    .fail(function(data) {
      controller.set('errorLoading', true);
    });
  },

  // Add display properties to a printer object.
  formatPrinter: function(printer) {
    var floor = App.util.roomToFloor(printer.room);
    if (floor) {
      printer.displayFloor = floor;
      printer.displayRoom = 'room ' + printer.room;
    } else {
      printer.displayFloor = '';
      printer.displayRoom = printer.room;
    }

    printer.displayPublic = printer.public ? '' : '- private';

    // Describe the printer type.
    // ex: MFD printer, Laser color printer
    printer.displayType = printer.type;
    printer.displayType += printer.color ? ' color printer' : ' printer';

    return printer;
  }

});

App.CampusMapController = Ember.ObjectController.extend({
  needs: ['printers'],

  mapLoaded: false,
  printersLoaded: false,
  selected: null,
  active: null,

  defaultColor: '#b4b4b4',
  hoverColor: '#4dafcf',
  selectedColor: '#007095',
  _svgDocument: null,

  svgDocument: function() {
    var value = this.get('_svgDocument');
    if (!value) {
      value = document.getElementById('campus-map').contentDocument;
      this.set('_svgDocument', value);
    }
    return value;
  }.property('_svgDocument'),

  svgBuilding: function(group) {
    return this.get('svgDocument').getElementById(group.id);
  },

  // Set a building as selected.
  select: function(group) {
    if (this.get('selected')) {
      var previousBuilding = this.svgBuilding(this.get('selected'));
      this.setColor(previousBuilding, this.get('defaultColor'));
    }
    if (this.get('mapLoaded')) {
      this.setColor(group, this.get('selectedColor'));
    }
    
    this.set('selected', group);
    this.set('active', group);
  },

  // Set the color of a building.
  setColor: function(group, color) {
    this.svgBuilding(group).style.fill = color;
  },

  isSelected: function(group) {
    return group.id === this.get('selected').id;
  },

  // Add event listeners to the buildings in the campus map.
  bindMapButtons: function() {
    // Only bind if the map and printer list are loaded.
    if (!this.get('mapLoaded') || !this.get('printersLoaded')) {
      return;
    }

    var controller = this;
    // initialize the buildings
    _.each(this.get('controllers.printers.buildingGroups'), function(group) {
      var svgBuilding = controller.svgBuilding(group);
      svgBuilding.style.cursor = 'pointer';

      // initialize the color of each building
      if (controller.isSelected(group)) {
        var color = controller.get('selectedColor');
      } else {
        var color = controller.get('defaultColor');
      }
      controller.setColor(group, color);

      // Make buildings clickable.
      svgBuilding.addEventListener('click', function() {
        controller.select(group);
      });

      // Highlight buildings on mouseover.
      svgBuilding.addEventListener('mouseover', function() {
        // If the mouse leaves the building before 100ms is up, 'hover' will
        // be set to false and the building will not be highlighted.
        $.data(this, 'hover', true);
        if (!controller.isSelected(group)) {
          controller.setColor(group, controller.get('hoverColor'));
        }

        // Delay 100ms before activating.
        _.delay(function() {
          if ($(svgBuilding).data('hover')) {
            controller.set('active', group);
          }
        }, 100);
      });

      // Unhilight buildings on mouseleave.
      svgBuilding.addEventListener('mouseleave', function() {
        $.data(this, 'hover', false);
        if (!controller.isSelected(group)) {
          controller.setColor(group, controller.get('defaultColor'));
          controller.set('active', controller.get('selected'));
        }
      });
    });
  }

});

App.CampusMapView = Ember.View.extend({
  templateName: 'campusMap',

  didInsertElement: function() {
    // get svg map and wait for it to load
    var mapObject = document.getElementById('campus-map');
    var view = this;
    mapObject.addEventListener('load', function() {
      view.get('controller').set('mapLoaded', true);
      view.get('controller').bindMapButtons();
    });
  }
});

App.util = {
  formatMoney: function(number, afterDecimal) {
    afterDecimal = afterDecimal || 2;
    number = number || 0;
    return '$' + parseFloat(number, 10).toFixed(afterDecimal);
  },

  showAlert: function(selector) {
    var alert = $(selector);
    alert.show();
    var closeButton = alert.find('a');
    closeButton.one('click', function(event) {
      alert.hide();
      event.preventDefault();
    });
  },

  // Given a room number, return the floor the room is on.
  // Return null when the answer is unknown.
  roomToFloor: function(room) {
    if (parseInt(room) === NaN) {
      return null;
    }
    // extract the first digit (the floor number)
    var floorNumber = parseInt(room[0], 10);
    return ['basement', 'first floor', 'second floor', 'third floor', 'fourth floor',
            'fifth floor', 'sixth floor', 'seventh floor', 'eighth floor', 'ninth floor'][floorNumber]
  }
};
