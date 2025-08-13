# Sample file formats for Site Sentinel

## Sample Excel format (websites.xlsx):
```
URL
https://google.com
https://github.com
https://stackoverflow.com
facebook.com
twitter.com
```

## Sample CSV format (websites.csv):
```
URL
https://google.com
https://github.com
https://stackoverflow.com
facebook.com
twitter.com
```

## Sample TXT format (websites.txt):
```
https://google.com
https://github.com
https://stackoverflow.com
facebook.com
twitter.com
```

Note: 
- For Excel and CSV files, the system will look for columns named "URL", "website", "domain", or "site"
- If none are found, it will use the first column
- For TXT files, put one website URL per line
- You can include or omit the https:// prefix - the system will add it automatically if missing
