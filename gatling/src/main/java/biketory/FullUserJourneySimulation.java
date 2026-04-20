package biketory;

import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Stream;

import io.gatling.javaapi.core.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

/**
 * Full user journey: register -> challenges -> upload -> leaderboard -> dashboard -> landing.
 * Totally independent from AllSimulation.
 *
 * Launch:
 *   mvn gatling:test -Dgatling.simulationClass=biketory.FullUserJourneySimulation \
 *       -DbaseUrl=http://localhost:8000 -Dusers=10 -DrampSeconds=20
 */
public class FullUserJourneySimulation extends BaseSimulation {

    private static final int USER_COUNT = Integer.getInteger("users", 5);
    private static final int RAMP_SECONDS = Integer.getInteger("rampSeconds", 10);
    private static final String RUN_ID = UUID.randomUUID().toString().substring(0, 8);

    private static Iterator<Map<String, Object>> journeyFeeder() {
        final int[] counter = {0};
        return Stream.generate((Supplier<Map<String, Object>>) () -> {
            int idx = ++counter[0];
            String uid = "journey_" + RUN_ID + "_" + idx;
            return Map.of(
                    "username", uid,
                    "email", uid + "@test.biketory.local",
                    "password", "Gat!ing_2026_Str0ng",
                    "gpxFile", "trace" + idx + ".gpx"
            );
        }).iterator();
    }

    // -- Step 1: Register + Login ------------------------------------------------

    private ChainBuilder strictRegister() {
        return fetchCsrf("GET /register/", "/register/")
                .pause(1, 2)
                .exec(
                        http("POST /register/")
                                .post("/register/")
                                .disableFollowRedirect()
                                .header("Referer", baseUrl + "/register/")
                                .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                                .formParam("email", "#{email}")
                                .formParam("password1", "#{password}")
                                .formParam("password2", "#{password}")
                                .check(status().is(302))
                );
    }

    // -- Step 2: Challenges — uses browseChallenges() from BaseSimulation --------

    // -- Step 3: Upload GPX + trace detail ---------------------------------------

    private ChainBuilder uploadAndViewTrace() {
        return exec(uploadGpx())
                .pause(1, 2)
                .exec(
                        http("GET trace detail")
                                .get("#{traceUrl}")
                                .check(status().is(200))
                );
    }

    // -- Step 4: Leaderboard -----------------------------------------------------

    private static ChainBuilder browseLeaderboard() {
        return exec(
                http("GET /leaderboard/")
                        .get("/leaderboard/")
                        .check(status().is(200))
        )
        .pause(1, 2)
        .exec(
                http("GET /leaderboard/surface/")
                        .get("/leaderboard/surface/")
                        .check(status().is(200))
        );
    }

    // -- Step 5: Dashboard -------------------------------------------------------

    private static ChainBuilder browseDashboard() {
        return exec(
                http("GET /dashboard/")
                        .get("/dashboard/")
                        .check(status().is(200))
        );
    }

    // -- Step 6: Landing ---------------------------------------------------------

    private static ChainBuilder browseLanding() {
        return exec(
                http("GET /")
                        .get("/")
                        .check(status().is(200))
        )
        .exec(
                http("GET /api/hexagons/")
                        .get("/api/hexagons/")
                        .check(status().is(200))
        );
    }

    // -- Scenario ----------------------------------------------------------------

    private ScenarioBuilder fullJourneyScenario() {
        return scenario("Full User Journey (" + USER_COUNT + " users)")
                .feed(journeyFeeder())
                // Step 1 — Register + Login
                .exec(strictRegister())
                .pause(1, 2)
                .exec(login())
                .pause(1, 2)
                // Step 2 — Challenges
                .exec(browseChallenges())
                .pause(1, 2)
                // Step 3 — Upload GPX
                .exec(uploadAndViewTrace())
                .pause(1, 2)
                // Step 4 — Leaderboard
                .exec(browseLeaderboard())
                .pause(1, 2)
                // Step 5 — Dashboard
                .exec(browseDashboard())
                .pause(1, 2)
                // Step 6 — Landing
                .exec(browseLanding());
    }

    {
        setUp(
                fullJourneyScenario()
                        .injectOpen(rampUsers(USER_COUNT).during(RAMP_SECONDS))
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(5000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
