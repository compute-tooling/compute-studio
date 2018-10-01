Database Setup
---------------------

Due to our reliance on the Postgres JSON field, a local Postgres installation
is required to run the app and its tests locally. COMP is compatible with Postgres 10,
and we recommend that you follow
the [Heroku instructions](https://devcenter.heroku.com/articles/heroku-postgresql#local-setup)
for local Postgres setup. Other useful resources are a postgres
[installation video](https://www.youtube.com/watch?v=xaWlS9HtWYw) and the
[Postgres.app installation documentation](http://postgresapp.com/documentation/install.html).

The default behavior is to work off of a local Postgres database
`comp_local_database`, and in `webapp_env.sh`, the Django database url
environment variable `DATABASE_URL` is set to `postgresql://localhost/comp_local_database`.
However, after running `source webapp_env.sh` you can update this variable
to point to other Postgres databases such as some other database named
`my_other_postgres_database`. Then, you update the database url to be
`postgresql://localhost/my_other_postgres_database`. This is useful if you
want to run some tests on the production or test app database, for example.


Database Migrations
---------------------

- Be very careful with data related to the results column
- Do a monthly database back up and keep the previous two months of production
  backups and one month of testing backups
- Examine the python migration code created by Django
- Examine the SQL migration code created by Django
- Always back up your data before running a migration
- Check that you can roll back your migrations
- Check how long it will take to run a migration (most of ours are fairly
  quick)
