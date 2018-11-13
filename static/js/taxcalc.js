var currentYear = $('#start-year-select').val();
$('#start-year-select').change(function(e) {
  $('#current-year-link').attr('href', '/taxcalc/?start_year=' + $(this).val() + '&data_source=' + $('#data-source-select').val());
  $('#current-year-modal').modal('show');
});

$('#current-year-modal').on('hide.bs.modal', function (e) {
  $('#start-year-select option').removeAttr("selected");
  $('#start-year-select option[value="' + currentYear + '"]').attr("selected", "selected");
});

var dataSource = $('#data-source-select').val();
$('#data-source-select').change(function(e) {
    $('#data-source-link').attr('href', '/taxcalc/?start_year=' + $('#start-year-select').val() + '&data_source=' + $(this).val());
    $('#data-source-modal').modal('show');
});

$('#data-choice-modal').on('hide.bs.modal', function (e) {
  $('#data-source option').removeAttr("selected");
  $('#data-source option[value="' + dataSource + '"]').attr("selected", "selected");
});


// Logic for CPI checkbox inputs:
// 1. disable hidden input if the displayed input is checked.
// 2. disable hidden and displayed inputs if user does not change it.
$("form").on("submit", function(e){
  $(this).find("input.model[type=checkbox]").each(function(){
    if($(this).prop("checked")){
      $("#hidden-" + $(this).prop("id")).prop("disabled", true);
    }
    if(!$(this).prop("check-edited")){
      $("#hidden-" + $(this).prop("id")).prop("disabled", true);
      $(this).prop("disabled", true);
    }
  })
});

