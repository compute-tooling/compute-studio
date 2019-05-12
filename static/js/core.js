$(document).ready(function() {
  $('[data-toggle="tooltip"]').tooltip();

  var toggleEdited = function(input) {
    value = input.val();
    value_default = input.prop("placeholder");
    value_changed = value != "" && value != value_default;
    default_node = $(`#default-${input.attr("name")}`);
    if (value_changed) {
      input.addClass("edited");
      default_node.removeClass("hide-default");
    } else {
      input.val(""); // show placeholder instead of value entered that = default
      input.removeClass("edited");
      default_node.addClass("hide-default");
    }
  };

  var toggleSelectEdited = function(select) {
    option = $("option:selected", select);
    value = option.val();
    value_default = select.attr("placeholder");
    value_changed = value != "" && value != value_default;
    console.log(value_default, value, select.attr("placeholder"));
    default_node = $(`#default-${select.attr("name")}`);
    if (value_changed) {
      select.removeClass("unedited");
      select.addClass("edited");
      default_node.removeClass("hide-default");
    } else {
      select.addClass("unedited");
      select.removeClass("edited");
      default_node.addClass("hide-default");
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
    select = $(this);
    toggleSelectEdited(select, this);
  });

  $("#inputs-form.model-param").submit(function(e) {
    $("select.form-control.model-param.unedited").each(function() {
      select = $(this);
      select.prop("disabled", true);
    });
  });

  $(".collapse-plus-minus").on("hidden.bs.collapse", function() {
    btn = $(`[data-target="#${$(this).attr("id")}"]`);
    btn.html('<i class="far fa-plus-square" style="size:5x;" ></i>');
  });
  $(".collapse-plus-minus").on("show.bs.collapse", function() {
    btn = $(`[data-target="#${$(this).attr("id")}"]`);
    btn.html('<i class="far fa-minus-square" style="size:5x;" ></i>');
  });
});
