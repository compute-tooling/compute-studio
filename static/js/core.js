
$(document).ready(function(){
  $('[data-toggle="tooltip"]').tooltip();

  $('.form-group > input.form-control').each(function() {
    // add edited class to be used for graying out edited fields.
    input = $(this)
    value = input.val()
    value_default = input.prop('placeholder');
    value_changed = (value != '') && (value != value_default);
    group = input.closest('.form-group')
    if (value_changed) {
      group.addClass('edited');
    } else {
      input.val(''); // show placeholder instead of value entered that = default
      group.removeClass('edited');
    }
  });

  $('select.form-control').change(function(e) {
    console.log($(this));
    $(this).removeClass("unedited");
  });

  $('#inputs-form').submit(function(e) {
    $(".unedited.select.form-control").each(function() {
      select = $(this);
      select.prop("disabled", true);
    });
  });
});
