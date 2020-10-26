# Readme for KB

## CCouch tool

### Database managment

List databases

Create database

Compact database

Delete database

### User management

List users

Users are stored in the `_users` database, which is global to the couchdb instance. Those
users can be associated with one or more databases. 

There are two types of users, `admins` and `members`.

`members` can create, update, read, and delete documents in a database.

`admins` can, in addition to what `members` can do, modify design documents and modify 
the database security object.

The database security object defines the users associated with a database, and the 
roles of those users.

Create user

Get user details

Delete user

Set user groups

List database users

Add user to database role

Remove user from database role
