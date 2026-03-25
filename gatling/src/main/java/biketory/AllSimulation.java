package biketory;

import java.util.UUID;

import static io.gatling.javaapi.core.CoreDsl.*;

/**
 * Runs all scenarios sequentially:
 * 1. Public browsing
 * 2. Registration
 * 3. Upload + stats verification
 */
public class AllSimulation extends BaseSimulation {

    private static final String RUN_ID = UUID.randomUUID().toString().substring(0, 8);
    private static final String USER1 = "perf_" + RUN_ID + "_u1";
    private static final String USER2 = "perf_" + RUN_ID + "_u2";
    private static final String PASSWORD = "P@ss_" + RUN_ID + "!";

    {
        setUp(
                publicBrowsingScenario()
                        .injectOpen(atOnceUsers(1))
                        .andThen(
                                registrationScenario()
                                        .injectOpen(atOnceUsers(2))
                        )
                        .andThen(
                                uploadScenario(USER1, USER2, PASSWORD)
                                        .injectOpen(atOnceUsers(2))
                                        .andThen(
                                                verifyStatsScenario(USER1, USER2)
                                                        .injectOpen(atOnceUsers(1))
                                        )
                        )
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(5000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
