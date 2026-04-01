package biketory;

import java.util.UUID;

import static io.gatling.javaapi.core.CoreDsl.*;

public class AuthenticatedBrowsingSimulation extends BaseSimulation {

    private static final String RUN_ID = UUID.randomUUID().toString().substring(0, 8);
    private static final String USERNAME = "perf_auth_" + RUN_ID;
    private static final String PASSWORD = "P@ss_" + RUN_ID + "!";

    {
        setUp(
                authenticatedBrowsingScenario(USERNAME, PASSWORD)
                        .injectOpen(atOnceUsers(1))
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(2000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
