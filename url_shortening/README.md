# URL Shortening Application

## Requirements

### Functional requirements

We want an application that takes a URL as an input, and returns a short URL as
an output, called an alias. This is useful to facilitate sharing long URLs,
because they take much less space and are users make less errors when typing
them.

Upon accessing a short URL, the user is redirected to the original URL.

The short URL is generated automatically, but a user may choose to use its own
short URL. The application will verify the user-defined short URL is not
already taken, and is long enough.

Short URLs will expire after a certain amount of time, but the user can also
choose the time interval before expiration.

A user can create an account, although this is not mandatory to use the
application. With an account, a user can review his URLs and manage them:
review, create, update, and delete.

We should have quotas and API rate limiters to prevent abuse of the
application.

### Non-functional requirements

Storage of long and short URLs should be very durable, with a very low risk of
the system losing data.

Users should be able to access the original URL from a short URL very quickly,
in less than a second.

Our application should be highly available, especially to let users be
redirected from a short URL to the original URL. The functionality that creates
short URLs may be unavailable for small time intervals.

## Capacity estimation

We carry out estimates using powers of ten. For example, if we indicated a
value of 10^2, it means we expect a value between 100 and 1000.

We will build a system that can support 10^8 (100 million) daily users.

We estimate there will be 10^7 short URLs created per day or 10^2 per second,
and that each URL will be accessed 10^2 times, leading to 10^9 reads per day or
10^4 per second.

If we store URLs for up to 5 years, we will store 10^10 URLs in total (10
billion).

If storing a URL and its alias takes 10^2 bytes, we will need up to 10^12 bytes
of storage (1 TB).

Coming back to read and write throughput, there will be 10^2 bytes * 10^4 =
10^6 bytes (1 MB) per second of read traffic, and 10^4 (10 KB) of write
traffic.

## System API

All functions accept a username and an API key as optional parameters, for
users that have an account.

`create_url` creates an alias and has the parameters:
* url (string): Original URL to be shortened (required).
* ttl (int): Time-to-live for the URL, in hours, stored as an expiration
  timestamp in the database (optional).
* alias (string): Desired alias (optional).
* Returns: code indicating success or failure.

`get_url` maps an alias to the original URL:
* alias (string): Short URL.
* Returns (string): Original URL or null if alias does not exist.

`get_urls_by_user` retrieves the aliases created by a user:
* user_name (string): Username.
* Returns (list): List of URLs created by the user.

`delete_url` deletes an alias:
* alias (string): Short URL.
* Returns: code indicating success or failure.

## Data model

We need the following tables:

* users
    * user_name (string, primary key)
    * first_name (string)
    * last_name (string)
    * joined_on (timestamp)
    * password (string)
    * last_login (timestamp)

* urls
    * alias (string, primary key)
    * original (string)
    * created_by (string)
    * created_on (timestamp)
    * ttl (timestamp)
    * accesses (obj)
        * accessed_on (timestamp)

Given the estimated application throughput, a distributed key-value or document
store is appropriate.

We will shard the users table by `user_name` because it has unique values
(maximum cardinality). The value should be hashed to decrease the
probability of hot shards. Range-based sharding would not perform as well
because user names do not use the full range of possible strings.

The urls table will be sharded by alias. We can use range-based sharding
because all possible values for aliases are used.

To increase the performance of retrieving URLs created by a logged user, we
will create an index on the field `created_by` in the `urls` table.

## Short URL generation

We want to store 10 billion short URLs. If we use all ASCII letters (both upper
and lower cases), digits, hyphen, underscore and period characters, we need 6
characters (65^6 is approximately equal to 75 billion).

A simple solution would be to hash the original URL using an algorithm such as
MD5 or SHA, then convert it to a string. However, the resulting string would
exceed 6 characters, so we may truncate the string but risk having alias
collisions (several URLs having the same alias). To solve this, adding the user
ID to the original URL or an incrementing number (for non-logged users) would
solve the problem.

Another solution is to pre-generate URL aliases, store them in a database, and
get a key when a new alias is created. This solution will allow us to quickly
get an alias, and prevent any collision. When an alias is used, it should be
removed from the alias database to make sure it is not used again. ACID
transaction would help ensuring that an alias cannot be used but more than one
time. Instead of always querying the alias database to store a new URL, a few
aliases can be loaded into memory. If a server crashes, the aliases remaining
in memory will be wasted, but this is acceptable because we pre-generated
aliases in excess. The total storage necessary will be 1 byte * 6 characters *
75 billion aliases = 452 GB.

## High-level design

Our application will be presented as a website and as an API.

Our system will have, at a minimum, the following components:
* application servers run the website and the API, store and retrieve URL
  aliases
* general database servers store the users and aliases tables
* alias key database servers store the pre-generated aliases

We will keep application servers stateless, allowing us to scale the
application by adding more application servers. Load balancers will balance
traffic from clients to the cluster of application servers.
