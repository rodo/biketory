package biketory;

import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Stream;

import io.gatling.javaapi.core.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

/**
 * N users register, log in, and each upload a unique GPX trace.
 * Totally independent from AllSimulation.
 *
 * Launch:
 *   mvn gatling:test -Dgatling.simulationClass=biketory.MassUploadSimulation \
 *       -DbaseUrl=http://localhost:8000 -Dusers=50
 */
public class MassUploadSimulation extends BaseSimulation {

    private static final int USER_COUNT = Integer.getInteger("users", 2);
    private static final String RUN_ID = UUID.randomUUID().toString().substring(0, 8);

    private static Iterator<Map<String, Object>> massUploadFeeder() {
        final int[] counter = {0};
        return Stream.generate((Supplier<Map<String, Object>>) () -> {
            int idx = ++counter[0];
            String uid = "mass_" + RUN_ID + "_" + idx;
            return Map.of(
                    "username", uid,
                    "email", uid + "@test.biketory.local",
                    "password", "Gat!ing_2026_Str0ng",
                    "gpxFile", "trace" + idx + ".gpx"
            );
        }).iterator();
    }

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

    private ScenarioBuilder massUploadScenario() {
        return scenario("Mass Upload (" + USER_COUNT + " users)")
                .feed(massUploadFeeder())
                .exec(strictRegister())
                .pause(1, 2)
                .exec(
                        http("GET /upload/ (auth check)")
                                .get("/upload/")
                                .disableFollowRedirect()
                                .check(status().is(200))
                )
                .pause(1, 2)
                .exec(uploadGpx())
                .pause(1, 2)
                .exec(
                        http("GET trace detail")
                                .get("#{traceUrl}")
                                .check(status().is(200))
                );
    }

    {
        setUp(
                massUploadScenario()
                        .injectOpen(rampUsers(USER_COUNT).during(30))
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(5000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
