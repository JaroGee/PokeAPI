const form = document.querySelector(".search-card");
const searchInput = document.getElementById("search-input");
const suggestionsList = document.getElementById("suggestions");
const historyContainer = document.getElementById("results");
const categoryFilter = document.getElementById("category-filter");
const randomButton = document.getElementById("random-button");
const prevPageButton = document.getElementById("prev-page");
const nextPageButton = document.getElementById("next-page");
const historySummary = document.getElementById("history-summary");

const PAGE_SIZE = 8;
const MAX_HISTORY = 64;
const PIXEL_ICON_SRC = window.PIXEL_ICON_SRC;

let debounceTimer;
let searchHistory = [];
let currentPage = 0;

const debounce = (fn, delay = 200) => {
  return (...args) => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => fn(...args), delay);
  };
};

const buildQueryParams = () => {
  const params = new URLSearchParams();
  const value = searchInput.value.trim();
  if (value) params.set("q", value);
  const filter = categoryFilter.value.trim();
  if (filter) params.set("filter", filter);
  return params.toString();
};

const updateSuggestions = async () => {
  const query = buildQueryParams();
  if (!query) {
    suggestionsList.classList.remove("visible");
    suggestionsList.innerHTML = "";
    return;
  }

  try {
    const response = await fetch(`${SUGGESTIONS_ENDPOINT}?${query}`);
    if (!response.ok) throw new Error("Failed to fetch suggestions");
    const { suggestions } = await response.json();
    renderSuggestions(suggestions);
  } catch (error) {
    console.error(error);
  }
};

const renderSuggestions = (suggestions) => {
  suggestionsList.innerHTML = "";
  if (!suggestions.length) {
    suggestionsList.classList.remove("visible");
    return;
  }

  suggestionsList.classList.add("visible");
  suggestions
    .slice(0, 10)
    .forEach(({ name, category, index }) => {
      const item = document.createElement("li");
      item.setAttribute("role", "option");
      item.innerHTML = `<span>${name}</span><span class="meta">#${index} · ${category}</span>`;
      item.addEventListener("click", () => {
        searchInput.value = name;
        suggestionsList.classList.remove("visible");
        performSearch();
      });
      suggestionsList.appendChild(item);
    });
};

const createSectionBlock = ({ title, items }) => {
  const block = document.createElement("div");
  block.className = "section-block";

  const heading = document.createElement("h4");
  heading.textContent = title;
  block.appendChild(heading);

  const list = document.createElement("ul");
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  block.appendChild(list);
  return block;
};

const createResultCard = (entry) => {
  const card = document.createElement("article");
  card.className = "result-card";

  const header = document.createElement("div");
  header.className = "card-header";

  const textWrap = document.createElement("div");
  const name = document.createElement("div");
  name.className = "name";
  name.textContent = entry.name;
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${entry.category} · #${entry.index}`;
  textWrap.append(name, meta);

  const icon = document.createElement("img");
  icon.className = "pixel-icon";
  icon.src = PIXEL_ICON_SRC;
  icon.alt = "Pixel Pokémon icon";

  header.append(textWrap, icon);

  const description = document.createElement("p");
  description.className = "description";
  description.textContent = entry.description;

  const sectionGrid = document.createElement("div");
  sectionGrid.className = "section-grid";
  entry.sections.forEach((section) => {
    sectionGrid.appendChild(createSectionBlock(section));
  });

  card.append(header, description, sectionGrid);
  return card;
};

const renderHistory = () => {
  historyContainer.innerHTML = "";

  if (!searchHistory.length) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.innerHTML = "<p>No adventures yet. Search for a Pokémon or roll the Random Poké Ball!</p>";
    historyContainer.appendChild(emptyState);
    historySummary.textContent = "0 searches";
    prevPageButton.disabled = true;
    nextPageButton.disabled = true;
    return;
  }

  const total = searchHistory.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  currentPage = Math.min(currentPage, totalPages - 1);

  const start = currentPage * PAGE_SIZE;
  const pageItems = searchHistory.slice(start, start + PAGE_SIZE);

  pageItems.forEach((group) => {
    const groupEl = document.createElement("article");
    groupEl.className = "history-group";

    const header = document.createElement("header");
    const title = document.createElement("h3");
    title.textContent = group.label;

    const meta = document.createElement("div");
    meta.className = "history-meta";
    meta.innerHTML = [
      group.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      group.filter ? `Filter: ${group.filter}` : null,
      group.shortcuts.length ? `Shortcuts: ${group.shortcuts.join(", ")}` : null,
    ]
      .filter(Boolean)
      .join(" · ");

    header.append(title, meta);

    const entriesWrap = document.createElement("div");
    entriesWrap.className = "entry-grid";

    if (!group.entries.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.innerHTML = `<p>No matches for "${group.queryDisplay}". Try new keywords or filters.</p>`;
      entriesWrap.appendChild(empty);
    } else {
      group.entries.forEach((entry) => {
        entriesWrap.appendChild(createResultCard(entry));
      });
    }

    groupEl.append(header, entriesWrap);
    historyContainer.appendChild(groupEl);
  });

  const startCount = start + 1;
  const endCount = Math.min(start + PAGE_SIZE, total);
  historySummary.textContent = `Showing ${startCount}-${endCount} of ${total} searches`;

  prevPageButton.disabled = currentPage === 0;
  nextPageButton.disabled = currentPage >= totalPages - 1;
};

const addToHistory = (group) => {
  searchHistory.unshift(group);
  if (searchHistory.length > MAX_HISTORY) {
    searchHistory = searchHistory.slice(0, MAX_HISTORY);
  }
  currentPage = 0;
  renderHistory();
};

const performSearch = async () => {
  const params = buildQueryParams();
  const url = params ? `${SEARCH_ENDPOINT}?${params}` : SEARCH_ENDPOINT;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to fetch search results");
    const data = await response.json();
    addToHistory({
      label: data.query && data.query.trim() ? `Search: ${data.query.trim()}` : "Search: Full Library",
      queryDisplay: data.query && data.query.trim() ? data.query.trim() : "Full Library",
      entries: data.results,
      filter: categoryFilter.value.trim(),
      shortcuts: Object.entries(data.shortcuts || {}).map(([key, value]) => `@${key}="${value}"`),
      timestamp: new Date(),
    });
  } catch (error) {
    console.error(error);
  }
};

const fetchRandom = async () => {
  try {
    const response = await fetch(RANDOM_ENDPOINT);
    if (!response.ok) throw new Error("Failed to fetch random entry");
    const { label, result } = await response.json();
    addToHistory({
      label: label || `Random Spotlight: ${result.name}`,
      queryDisplay: result.name,
      entries: [result],
      filter: "Random",
      shortcuts: [],
      timestamp: new Date(),
    });
  } catch (error) {
    console.error(error);
  }
};

searchInput.addEventListener("input", debounce(updateSuggestions, 250));

searchInput.addEventListener("focus", () => {
  if (suggestionsList.innerHTML) {
    suggestionsList.classList.add("visible");
  }
});

document.addEventListener("click", (event) => {
  if (!form.contains(event.target)) {
    suggestionsList.classList.remove("visible");
  }
});

categoryFilter.addEventListener("change", () => {
  updateSuggestions();
  performSearch();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  performSearch();
});

randomButton.addEventListener("click", () => {
  fetchRandom();
});

prevPageButton.addEventListener("click", () => {
  if (currentPage > 0) {
    currentPage -= 1;
    renderHistory();
  }
});

nextPageButton.addEventListener("click", () => {
  const totalPages = Math.ceil(searchHistory.length / PAGE_SIZE);
  if (currentPage < totalPages - 1) {
    currentPage += 1;
    renderHistory();
  }
});

renderHistory();
