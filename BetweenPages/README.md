# BetweenPages

## Description

Between Pages is a Flask-based web application designed to help readers discover books based not only on what they already know, but also on the kind of reading experience they want. Instead of treating book discovery as a simple search for a title or author, the application gives users different ways to find their next story, including traditional book searches, alternative recommendations, personal shelves, favorites, and an AI-assisted reading companion called Book Buddy.

The project combines the Open Library API with Flask, HTML, CSS, and optional OpenAI functionality. The application is designed to be simple to navigate while giving readers more control over how they discover and organize books.

## The Problem It Solves

Finding a new book can be difficult when a reader knows what kind of experience they want but does not know the exact title to search for. A traditional search system usually requires the user to already have a specific book, author, or keyword in mind.

Between Pages addresses this problem by offering more than one path to discovery. Users can search directly for books, or they can provide a book they already enjoyed along with optional preferences and receive alternative books based on similar subjects, themes, and reading experiences.

The application also solves a second problem: keeping track of books after discovering them. Readers can organize books into different shelves and save favorites without needing to create an account.

## How It Works

When a user opens Between Pages, the home page presents two main discovery options: searching the catalog or finding alternatives. The Discover page allows users to search for books and authors through Open Library.

The alternative recommendation system starts by finding the book provided by the user. The application then examines information such as subjects and themes and can also use OpenAI, when configured, to identify genres, themes, vibes, and useful search terms. These details are combined with any preferences entered by the user. The application searches Open Library for possible matches and scores the results based on similarities between the original book, its subjects, and the user's preferences.

Users can then add books to one of four shelves: **Want to Read, Currently Reading, Read,** or **Didn't Finish**. They can also mark books as favorites. Shelf and favorite information is maintained through Flask sessions, so an account is not required.

Between Pages also includes **Book Buddy**, a reading companion that allows users to ask questions about books, such as questions about themes, morals, friendship, character decisions, or lessons. When OpenAI is available, Book Buddy uses it to generate a thoughtful discussion. The application also includes a fallback system based on Open Library metadata and predefined topic and book lenses, allowing Book Buddy to remain useful even when the AI service is unavailable.

## Main Features

### Book Search

Users can search for books and authors using the Open Library search API. Search results display useful information about each book, including its title, author, cover, and other available metadata.

### Alternative Recommendations

The "Find Alternatives" feature helps users discover books similar to one they already know. Recommendations can take into account subjects, themes, genres, and user preferences instead of relying only on the exact title or author.

### Personal Shelves

Users can organize books into four shelves:

* Want to Read
* Currently Reading
* Read
* Didn't Finish

Books can be added or removed from shelves directly from the Discover page.

### Favorites

Users can save books as favorites and access them from a dedicated Favorites page. Favorites can also be removed whenever the user wants.

### Book Buddy

Book Buddy acts as a reading discussion companion. Users can ask questions about themes, morals, character development, friendship, courage, identity, and other ideas connected to a book.

### Settings

The Settings page provides access to the application's dark-mode preference and explains how saved shelves and favorites are handled in the browser.

## Project Files and Their Roles

### `app.py`

`app.py` is the main Flask application and contains the backend logic for the project. It defines the application's routes, handles form submissions, manages Flask sessions, communicates with external APIs, processes book information, and generates alternative recommendations.

It contains the functions responsible for searching Open Library, finding an original book, analyzing book information, building alternative recommendations, managing shelves and favorites, and handling Book Buddy questions.

The file also contains error-handling and fallback logic so that the application can continue working when an external API or optional AI service is unavailable.

### `templates/base.html`

`base.html` is the shared layout used by the other pages. It provides the navigation bar, footer, Bootstrap resources, Bootstrap Icons, the stylesheet connection, and shared page structure. It also handles the application's global dark-mode preference using browser storage.

Using a shared base template avoids repeating the same navigation and layout code on every page and makes the application easier to maintain.

### `templates/BetweenPages.html`

`BetweenPages.html` is the home page. It introduces Between Pages and presents the two main discovery paths: searching the catalog and finding alternative books based on a reading experience.

### `templates/search.html`

`search.html` is the main Discover interface. It contains both search modes, displays book results, and provides controls for adding books to shelves or favorites. It also displays the appropriate empty states when a search does not produce results. In addition, it preserves the user's scroll position after adding a book to a shelf or favorites, since those actions reload the page.

### `templates/favorites.html`

`favorites.html` displays the books that the user has saved as favorites. It provides the book cover, title, and author when available, along with an option to remove a book from favorites. If there are no favorites, the page provides a link back to Discover.

### `templates/shelves.html`

`shelves.html` displays the user's four reading shelves. Each shelf contains the books assigned to it and provides controls for removing books.

### `templates/book_buddy.html`

`book_buddy.html` provides the interface for Book Buddy. It contains the question form, example questions, and the area where Book Buddy's answer is displayed.

### `templates/settings.html`

`settings.html` provides the application's settings interface. It includes the dark-mode control and information explaining how shelves and favorites are stored and how clearing browser data can affect them.

### `static/style.css`

`style.css` contains the visual styling for the application. It controls the layout, typography, navigation, book cards, buttons, forms, shelves, favorites, Book Buddy interface, settings page, responsive behavior, and dark-mode appearance.

## Design Choices

One of the main design choices was to separate the application into reusable templates using Flask and Jinja. The shared `base.html` template provides a consistent structure across the application while individual templates focus on the content and functionality of their specific pages.

Another important choice was to provide two different discovery methods. Direct search is useful when a reader already knows what they are looking for, while alternative recommendations are useful when the reader knows the type of experience they want but needs help finding a specific book.

The shelf system was also designed around the way readers naturally think about books. Instead of using only a single saved list, the application separates books into four stages, allowing users to keep track of what they plan to read, are currently reading, have finished, or decided not to finish.

I also chose to make an account unnecessary for the current prototype. Shelves and favorites are handled through Flask sessions, which keeps the interaction simple and avoids requiring users to provide personal information just to organize books.

Finally, Book Buddy was designed with a fallback system. OpenAI can provide more flexible answers when an API key is available, but the application can also generate responses using book metadata and predefined topic lenses. This makes the feature more reliable and prevents the entire experience from depending on a single external service.

## Technologies and APIs

Between Pages was built using:

* **Python**
* **Flask**
* **Jinja2 templates**
* **HTML**
* **CSS**
* **Bootstrap**
* **Bootstrap Icons**
* **Open Library API**
* **OpenAI API** as an optional service
* **Flask sessions** for temporary user-specific shelves and favorites

## Conclusion

Between Pages is a book discovery and organization application that combines traditional search with experience-based recommendations. It gives readers several ways to discover books, organize their reading, save favorites, and discuss ideas through Book Buddy.

The project was designed around the idea that finding a book should not always begin with knowing its title. Sometimes a reader knows a feeling, a theme, a type of character, or a previous book they enjoyed. Between Pages uses those different starting points to make discovering the next story more flexible and personal.
