package biketory;

import static io.gatling.javaapi.core.CoreDsl.*;

public class RegistrationSimulation extends BaseSimulation {

    {
        setUp(
                registrationScenario().injectOpen(atOnceUsers(2))
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(2000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
