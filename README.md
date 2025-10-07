# About

frontend and backend for idleak.net hosted @ gardnerresearch.org

- backends workers are python doing specific collection 
- workers write to supabase db
- frontends are static hosted at github
- frontend js connecting to the supabase db with anonkey to fetch collection result

# ToDo

- move supabase utils out of idransom and create own file
- add function to write when workers last executed to db
- create API layer for the frontend to access, not direct db access
- add workers for news feed
- add workers for telegram
- add workers for twitter (?)