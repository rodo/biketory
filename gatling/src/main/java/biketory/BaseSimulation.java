package biketory;

import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Stream;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public abstract class BaseSimulation extends Simulation {

    protected final String baseUrl = System.getProperty("baseUrl", "http://localhost:8000");

    protected final HttpProtocolBuilder httpProtocol = http
            .baseUrl(baseUrl)
            .acceptHeader("text/html,application/json")
            .acceptLanguageHeader("fr-FR,fr;q=0.9")
            .userAgentHeader("Gatling/Biketory")
            .disableFollowRedirect();

    // -- Chain builders (reusable request sequences) ----------------------------

    protected static ChainBuilder fetchCsrf(String name, String url) {
        return exec(
                http(name)
                        .get(url)
                        .check(status().is(200))
                        .check(css("input[name='csrfmiddlewaretoken']", "value")
                                .saveAs("csrfToken"))
        );
    }

    protected ChainBuilder register() {
        return fetchCsrf("GET /register/", "/register/")
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
                );
    }

    protected ChainBuilder login() {
        return fetchCsrf("GET /accounts/login/", "/accounts/login/")
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
                );
    }

    protected ChainBuilder uploadGpx() {
        return fetchCsrf("GET /upload/", "/upload/")
                .pause(1, 2)
                .exec(
                        http("POST /upload/")
                                .post("/upload/")
                                .header("Referer", baseUrl + "/upload/")
                                .formUpload("gpx_file", "#{gpxFile}")
                                .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                                .check(status().is(302))
                                .check(header("Location").saveAs("traceUrl"))
                );
    }

    // -- Feeders ----------------------------------------------------------------

    protected static Iterator<Map<String, Object>> registrationFeeder() {
        return Stream.generate((Supplier<Map<String, Object>>) () -> {
            String uid = UUID.randomUUID().toString().substring(0, 8);
            return Map.of(
                    "username", "user_" + uid,
                    "email", "user_" + uid + "@test.biketory.local",
                    "password", "P@ss_" + uid + "!"
            );
        }).iterator();
    }

    protected static Iterator<Map<String, Object>> uploadFeeder(
            String user1, String user2, String password) {
        return List.<Map<String, Object>>of(
                Map.of(
                        "username", user1,
                        "email", user1 + "@test.biketory.local",
                        "password", password,
                        "gpxFile", "user1_hexagons_12.gpx",
                        "expectedHexagons", 12
                ),
                Map.of(
                        "username", user2,
                        "email", user2 + "@test.biketory.local",
                        "password", password,
                        "gpxFile", "user2_hexagons_10.gpx",
                        "expectedHexagons", 10
                )
        ).iterator();
    }

    // -- Scenario builders ------------------------------------------------------

    protected static ScenarioBuilder publicBrowsingScenario() {
        return scenario("Navigation publique")
                .exec(http("Landing page").get("/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("API hexagons").get("/api/hexagons/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("API hexagons bbox").get("/api/hexagons/?bbox=-2,46,4,49").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Mentions légales").get("/legal/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Stats utilisateur").get("/stats/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Stats mensuelles").get("/stats/monthly/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Répartition").get("/stats/pie/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Badges").get("/stats/badges/").check(status().is(200)));
    }

    protected ScenarioBuilder registrationScenario() {
        return scenario("Création de compte")
                .feed(registrationFeeder())
                .exec(register());
    }

    protected ScenarioBuilder uploadScenario(String user1, String user2, String password) {
        return scenario("Upload traces")
                .feed(uploadFeeder(user1, user2, password))
                .exec(register())
                .pause(1, 2)
                .exec(login())
                .pause(1, 2)
                .exec(uploadGpx())
                .pause(1, 2)
                .exec(
                        http("GET trace detail")
                                .get("#{traceUrl}")
                                .check(status().is(200))
                );
    }

    protected ScenarioBuilder verifyStatsScenario(String user1, String user2) {
        return scenario("Verify stats")
                .exec(
                        http("GET /stats/pie/")
                                .get("/stats/pie/")
                                .check(status().is(200))
                                .check(bodyString().saveAs("pieBody"))
                )
                .exec(session -> {
                    String body = session.getString("pieBody");

                    int start = body.indexOf("const ALL = ");
                    if (start == -1) {
                        System.err.println("Chart data not found in /stats/pie/");
                        return session.markAsFailed();
                    }
                    start += "const ALL = ".length();
                    int end = body.indexOf(";", start);
                    String json = body.substring(start, end).trim();

                    boolean ok = true;
                    ok &= verifyHexagonCount(json, user1, 12);
                    ok &= verifyHexagonCount(json, user2, 10);

                    if (!ok) {
                        System.err.println("Hexagon count mismatch in chart data: " + json);
                        return session.markAsFailed();
                    }

                    System.out.println("Hexagon counts verified: "
                            + user1 + "=12, " + user2 + "=10");
                    return session;
                });
    }

    protected static boolean verifyHexagonCount(String json, String username, int expected) {
        int labelIdx = json.indexOf("\"" + username + "\"");
        if (labelIdx == -1) {
            System.err.println("User " + username + " not found in chart labels");
            return false;
        }

        int labelsStart = json.indexOf("[") + 1;
        String beforeLabel = json.substring(labelsStart, labelIdx);
        int position = 0;
        for (char c : beforeLabel.toCharArray()) {
            if (c == ',') position++;
        }

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
}
