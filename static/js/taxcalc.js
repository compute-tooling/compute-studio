// Logic for CPI checkbox inputs:
// 1. disable hidden input if the displayed input is checked.
// 2. disable hidden and displayed inputs if user does not change it.
$("form").on("submit", function(e){
  $(this).find("input.model[type=checkbox]").each(function(){
    if($(this).prop("checked")){
      $("#hidden-" + $(this).prop("id")).prop("disabled", true);
    } else {
      $(this).prop("disabled", true);
    }
    if(!$(this).prop("check-edited")){
      $("#hidden-" + $(this).prop("id")).prop("disabled", true);
      $(this).prop("disabled", true);
    }
  })
});

$(document).ready(function(){
  $('[data-toggle="tooltip"]').tooltip();
})