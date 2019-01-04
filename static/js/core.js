// Logic for CPI checkbox inputs:
// 1. disable hidden input if the displayed input is checked.
// 2. disable hidden and displayed inputs if user does not change it.
$("#inputs-form").submit(function(e){
  $(this).find("input.model[type=checkbox]").each(function(){
    if($(this).prop("checked")){
      $("#hidden-" + $(this).prop("id")).prop("disabled", true);
    } else {
      $(this).prop("disabled", true);
    }
    if(!$(this).prop("check-edited")){
      $("#hidden-" + $(this).prop("id")).prop("disabled", true);
      $(this).prop("disabled", false);
      $(this).prop("value", "");
    }
  })
});

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

})
