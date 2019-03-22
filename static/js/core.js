$(document).ready(function() {
  $('[data-toggle="tooltip"]').tooltip();

  var toggleEdited = function(input) {
    value = input.val();
    value_default = input.prop("placeholder");
    value_changed = value != "" && value != value_default;
    if (value_changed) {
      input.addClass("edited");
    } else {
      input.val(""); // show placeholder instead of value entered that = default
      input.removeClass("edited");
    }
  };

  $("input.form-control").blur(function() {
    // add edited class to be used for graying out edited fields.
    input = $(this);
    toggleEdited(input);
  });

  $("input.form-control").each(function() {
    // add edited class to be used for graying out edited fields.
    input = $(this);
    toggleEdited(input);
  });

  $("select.form-control").change(function(e) {
    console.log($(this));
    $(this).removeClass("unedited");
  });

  $("#inputs-form").submit(function(e) {
    $(".unedited.select.form-control").each(function() {
      select = $(this);
      select.prop("disabled", true);
    });
  });
});
