let filteredWords = [];

fetch('/api/filtered-words')
  .then(response => response.json())
  .then(data => {
    filteredWords = data;
  });

function checkContentForFilter(input) {
  let content = input.value.toLowerCase();
  let found = false;

  filteredWords.forEach(word => {
    if (content.includes(word)) {
      found = true;
      content = content.replace(new RegExp(`\\b(${word})\\b`, 'gi'), '<span class="text-danger underline">$1</span>');
    }
  });

  return found;
}

function validateForm() {
  const titleInput = document.getElementById("postTitle");
  const descInput = document.getElementById("postDescription");
  const submitBtn = document.querySelector("button[type='submit']");

  let titleFlag = checkContentForFilter(titleInput);
  let descFlag = checkContentForFilter(descInput);

  submitBtn.disabled = titleFlag || descFlag;
}

// Event bindings
document.addEventListener("DOMContentLoaded", function () {
  const titleInput = document.getElementById("postTitle");
  const descInput = document.getElementById("postDescription");

  titleInput.addEventListener("input", validateForm);
  descInput.addEventListener("input", validateForm);
});
