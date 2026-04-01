package biketory;

import java.util.UUID;

import static io.gatling.javaapi.core.CoreDsl.*;

/**
 * Upload GPX traces with two distinct users, then call the stats API
 * endpoints and verify the responses are coherent.
 *
 * Phase 1 — Two users register, log in and upload a GPX trace each.
 * Phase 2 — One user calls /api/stats/monthly/ and /api/stats/traces/
 *           and checks that:
 *           - every endpoint returns 200 with valid JSON;
 *           - labels and datasets arrays are present;
 *           - datasets contain expected labels and data arrays.
 */
public class UploadAndStatsApiSimulation extends BaseSimulation {

    private static final String RUN_ID = UUID.randomUUID().toString().substring(0, 8);
    private static final String USER1 = "perf_" + RUN_ID + "_u1";
    private static final String USER2 = "perf_" + RUN_ID + "_u2";
    private static final String PASSWORD = "P@ss_" + RUN_ID + "!";

    {
        setUp(
                uploadScenario(USER1, USER2, PASSWORD)
                        .injectOpen(atOnceUsers(2))
                        .andThen(
                                verifyStatsApiScenario()
                                        .injectOpen(atOnceUsers(1))
                        )
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(5000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
