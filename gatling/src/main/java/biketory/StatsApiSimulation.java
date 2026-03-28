package biketory;

import static io.gatling.javaapi.core.CoreDsl.*;

public class StatsApiSimulation extends BaseSimulation {

    {
        setUp(
                statsApiScenario().injectOpen(atOnceUsers(1))
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(2000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
