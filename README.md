# Distributed Trace Visualization
#### UC-Berkeley MIDS W209 SP2021 Final Project

### Generating Zipkin Sample Data

1. Install Dependencies
You will need docker and docker-compose setup. 
You will need `maven` for building `synthetic-load-generator`.

2. Clone Repositories
Create a directory, and clone these github repositories: 
* https://github.com/Omnition/synthetic-load-generator
* https://github.com/openzipkin-attic/docker-zipkin

3. Start Zipkin-slim
Probably any of the zipkin containers are fine, but the slim version starts up more quickly than the others. Since we are only generating synthetic traces, we do not need to have persistent storage for zipkin.
```bash
cd docker-zipkin
docker-compose -f docker-compose-slim.yml up
```

4. Build and run the load generation tool
Load generation will simulate the execution of traces in a distributed environment, based on a hypothetical service topology specified in a json format. The topology can be customized to simulate various situations that may be amenable to visualization.
Assuming you used defaults for starting up zipkin-slim, here's how you would generate traces from one of the example topologies:
```bash
cd synthetic-load-generator
# only need to do the next line once
mvn package
# run the load generation process
java -jar ./target/SyntheticLoadGenerator-1.0-SNAPSHOT-jar-with-dependencies.jar --paramsFile ./topologies/hipster-shop.json --zipkinV2Proto3Url http://localhost:9411
```

5. Run a script to save trace json to a directory
TODO(jtrobec): we should be able to capture the output from the load generation tool, which contains trace IDs. A very simple script should be able to parse out these trace IDs, then hit the zipkin APIs to download the json into a folder.
