$(document).ready(function() {
  $('[data-toggle="tooltip"]').tooltip();

  var toggleEdited = function(input) {
    value = input.val();
    value_default = input.prop("placeholder");
    value_changed = value != "" && value != value_default;
    default_value = $(`#default-${input.attr("name")}`);
    if (value_changed) {
      input.addClass("edited");
      default_value.removeClass("hide-default");
    } else {
      input.val(""); // show placeholder instead of value entered that = default
      input.removeClass("edited");
      default_value.addClass("hide-default");
    }
  };

  $("input.form-control.model-param").blur(function() {
    // add edited class to be used for graying out edited fields.
    input = $(this);
    toggleEdited(input);
  });

  $("input.form-control.model-param").each(function() {
    // add edited class to be used for graying out edited fields.
    input = $(this);
    toggleEdited(input);
  });

  $("select.form-control.model-param").change(function(e) {
    console.log($(this));
    $(this).removeClass("unedited");
  });

  $("#inputs-form.model-param").submit(function(e) {
    $(".unedited.select.form-control").each(function() {
      select = $(this);
      select.prop("disabled", true);
    });
  });
});
