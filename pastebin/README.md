# Pastebin

## Requirements

### Functional requirements

Pastebin is a text storage and sharing web application.

Users can store short texts, which is then accessible at a specific URL, and
share the URL publicly or with a group of contacts.

Texts have an adjustable expiration date after which they are deleted from the
website.

Users can signup and authenticated or store text anonymously as unauthenticated
"guests".

### Non-functional requirements

The application should be highly available, basically always reachable.

Availability is more important that consistency: if a group of users does not
see an update for a short period of time, it's acceptable.

Data storage durability is crucial: text uploaded by users should never be
lost.

## Capacity estimations

We will accomodate 10^8 registered users, and we expect 10^7 daily active
users.

A paste is 10^5 bytes on average (limited to 500 KB).

There are 10^6 pastes writes per day (10^1 pastes writes per second, 10^8
pastes writes per year), and 10^7 paste reads per day (10^2 pastes reads per
second).

Write traffic is 10^6 bytes per second on average, read traffic is 10^7 bytes
per second on average.

Pastes will be stored for up to 5 years, so we may store up to 5 x 10^8 pastes,
totalizing 5 x 10^13 bytes (50 TB) of pastes.

## Interface

The following functions compose the application programming interface (all
functions have the user ID as a parameter, so it is ommitted):

* store_text(text_body, ttl): Stores a text entered by a user, with a given
  time-to-live (ttl).

* retrieve_text(text_id): Returns a text that was previously stored.

## Data model

We need to store information about users and stored texts. Texts will be stored
in a object store, such as AWS S3, and their metadata will be stored in a
database. Storing the text in an object store will allow to ease traffic on
the database and keep the metadata database size low.

The table 'users' has the following columns:

* username (string, primary key)
* first_name (string)
* last_name (string)
* joined_date (date)
* last_connected_date (date)

With 10^8 users, the table would contain 10^8 records. Assuming a record size
of 10^2 bytes, the table would store 10^10 bytes (10 GB).

The table 'texts' has the following columns:

* text_id (string, primary key)
* text_path (string): path to the text object in the object store
* created_by (string): username of the text creator
* creation_date (date)
* expiration_date (date): date after which the text should be deleted

With 5 x 10^8 stored texts, the table would contain 5 x 10^8 records. Assuming
a record size of 100 bytes, the table would store 5 x 10^10 bytes (50 GB).

The 'users' and 'texts' tables totalize 60 GB, a modest size for a database.
Given that we expect a few hundreds of requests per second (mostly reads), a
relational database such as PostgreSQL or MySQL would fulfill our requirements.

## High-level design

### Application workflow

When a user stores a text, a unique text identifier is assigned to the text to
serve as a URL for the text. The text is stored in an object store, such as AWS
S3. Text metadata is stored in the metadata database. As described in the
data model section, we will use a relational database for the metadata
database.

How long should be the text identifier? In the next 5 years we will have to
store 5 x 10^8 texts, so we will need as many identifiers. If we use 64
characters (uppercase and lowercase English letters, digits, hyphen and
underscore), a 5-character identifier should be enough: 64 ^ 5 equal
approximately 1 billion, which gives a 10-fold headroom. As discussed in the
design document for the URL shortening service, we will pre-generate text
identifiers and have a service manage them. The text storage application will
request a new text identifier from the identifier service when needed.

When a user requests an existing text, he uses the text identifier. The
corresponding text is retrieve from the object store and presented to the user.

### Infrastructure components


## Detailed design

### User quotas

Unauthenticated users will be allowed 10 "pastes" per day, while
authenticated users will be allowed 100 pastes per day. We could have a paid
subscription with increased user quotas.
