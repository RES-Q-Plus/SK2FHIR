Once you have cloned the repository, run the following command to build and start the containers:

```bash 
docker compose up
```

# Ports

Snowstorm: http://localhost:8081/swagger-ui/index.html
Validator API: http://localhost:8085/swagger-ui/index.html


# Validator

For the API to work correctly, you must upload a valid FHIR Bundle in JSON format. 
As follows [Download bundle examples](./bundles.zip)

# SNOWSTORM
To upload SNOMED CT codes, see https://github.com/IHTSDO/snowstorm/blob/master/docs/loading-snomed.md.

If you don't upload the SNOMED CT codes, the validator will show errors related to SNOMED CT.

