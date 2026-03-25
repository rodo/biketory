package biketory;

import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class UploadAndStatsSimulation extends Simulation {

    private final String baseUrl = System.getProperty("baseUrl", "http://localhost:8000");
    private static final String RUN_ID = UUID.randomUUID().toString().substring(0, 8);
    private static final String USER1 = "perf_" + RUN_ID + "_u1";
    private static final String USER2 = "perf_" + RUN_ID + "_u2";
    private static final String PASSWORD = "P@ss_" + RUN_ID + "!";

    private static final Iterator<Map<String, Object>> uploadFeeder = List.<Map<String, Object>>of(
            Map.of(
                    "username", USER1,
                    "email", USER1 + "@test.biketory.local",
                    "password", PASSWORD,
                    "gpxFile", "user1_hexagons_12.gpx",
                    "expectedHexagons", 12
            ),
            Map.of(
                    "username", USER2,
                    "email", USER2 + "@test.biketory.local",
                    "password", PASSWORD,
                    "gpxFile", "user2_hexagons_10.gpx",
                    "expectedHexagons", 10
            )
    ).iterator();

    private final HttpProtocolBuilder httpProtocol = http
            .baseUrl(baseUrl)
            .acceptHeader("text/html,application/json")
            .acceptLanguageHeader("fr-FR,fr;q=0.9")
            .userAgentHeader("Gatling/Biketory")
            .disableFollowRedirect();

    // -- Phase 1: register, login, upload GPX -----------------------------------

    private final ScenarioBuilder upload = scenario("Upload traces")
            .feed(uploadFeeder)

            // Register
            .exec(
                    http("GET /register/")
                            .get("/register/")
                            .check(status().is(200))
                            .check(css("input[name='csrfmiddlewaretoken']", "value")
                                    .saveAs("csrfToken"))
            )
            .pause(1, 2)
            .exec(
                    http("POST /register/")
                            .post("/register/")
                            .header("Referer", baseUrl + "/register/")
                            .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                            .formParam("username", "#{username}")
                            .formParam("email", "#{email}")
                            .formParam("password1", "#{password}")
                            .formParam("password2", "#{password}")
                            .check(status().is(302))
                            .check(header("Location").is("/"))
            )
            .pause(1, 2)

            // Login
            .exec(
                    http("GET /accounts/login/")
                            .get("/accounts/login/")
                            .check(status().is(200))
                            .check(css("input[name='csrfmiddlewaretoken']", "value")
                                    .saveAs("csrfToken"))
            )
            .pause(1, 2)
            .exec(
                    http("POST /accounts/login/")
                            .post("/accounts/login/")
                            .header("Referer", baseUrl + "/accounts/login/")
                            .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                            .formParam("username", "#{username}")
                            .formParam("password", "#{password}")
                            .check(status().is(302))
                            .check(header("Location").is("/upload/"))
            )
            .pause(1, 2)

            // Upload GPX
            .exec(
                    http("GET /upload/")
                            .get("/upload/")
                            .check(status().is(200))
                            .check(css("input[name='csrfmiddlewaretoken']", "value")
                                    .saveAs("csrfToken"))
            )
            .pause(1, 2)
            .exec(
                    http("POST /upload/")
                            .post("/upload/")
                            .header("Referer", baseUrl + "/upload/")
                            .formUpload("gpx_file", "#{gpxFile}")
                            .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                            .check(status().is(302))
                            .check(header("Location").saveAs("traceUrl"))
            )
            .pause(1, 2)

            // View trace detail
            .exec(
                    http("GET trace detail")
                            .get("#{traceUrl}")
                            .check(status().is(200))
            );

    // -- Phase 2: verify hexagon counts on stats page ---------------------------

    private final ScenarioBuilder verifyStats = scenario("Verify stats")
            .exec(
                    http("GET /stats/pie/")
                            .get("/stats/pie/")
                            .check(status().is(200))
                            .check(bodyString().saveAs("pieBody"))
            )
            .exec(session -> {
                String body = session.getString("pieBody");

                // Extract JSON from: const ALL = {...};
                int start = body.indexOf("const ALL = ");
                if (start == -1) {
                    System.err.println("Chart data not found in /stats/pie/");
                    return session.markAsFailed();
                }
                start += "const ALL = ".length();
                int end = body.indexOf(";", start);
                String json = body.substring(start, end).trim();

                // Verify each user has the expected hexagon count
                // JSON: {"labels":["user1","user2"],"datasets":[{"data":[12,10],...}]}
                boolean ok = true;
                ok &= verifyHexagonCount(json, USER1, 12);
                ok &= verifyHexagonCount(json, USER2, 10);

                if (!ok) {
                    System.err.println("Hexagon count mismatch in chart data: " + json);
                    return session.markAsFailed();
                }

                System.out.println("Hexagon counts verified: "
                        + USER1 + "=12, " + USER2 + "=10");
                return session;
            });

    private static boolean verifyHexagonCount(String json, String username, int expected) {
        // Find index of username in labels array
        int labelIdx = json.indexOf("\"" + username + "\"");
        if (labelIdx == -1) {
            System.err.println("User " + username + " not found in chart labels");
            return false;
        }

        // Count commas before this label in the labels array to get position
        int labelsStart = json.indexOf("[") + 1;
        String beforeLabel = json.substring(labelsStart, labelIdx);
        int position = 0;
        for (char c : beforeLabel.toCharArray()) {
            if (c == ',') position++;
        }

        // Find data array and get value at same position
        int dataIdx = json.indexOf("\"data\"");
        if (dataIdx == -1) {
            System.err.println("data array not found in chart JSON");
            return false;
        }
        int dataArrayStart = json.indexOf("[", dataIdx) + 1;
        int dataArrayEnd = json.indexOf("]", dataArrayStart);
        String[] values = json.substring(dataArrayStart, dataArrayEnd).split(",");

        if (position >= values.length) {
            System.err.println("Position " + position + " out of bounds for data array");
            return false;
        }

        int actual = Integer.parseInt(values[position].trim());
        if (actual != expected) {
            System.err.println("User " + username + ": expected " + expected
                    + " hexagons, got " + actual);
            return false;
        }
        return true;
    }

    {
        setUp(
                upload.injectOpen(atOnceUsers(2))
                        .andThen(
                                verifyStats.injectOpen(atOnceUsers(1))
                        )
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(5000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
