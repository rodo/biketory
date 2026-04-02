package biketory;

import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;
import java.util.stream.Stream;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public abstract class BaseSimulation extends Simulation {

    /** Shared map for passing referral tokens between sponsor and referee phases. */
    protected static final ConcurrentHashMap<String, String> referralTokens = new ConcurrentHashMap<>();

    protected final String baseUrl = System.getProperty("baseUrl", "http://localhost:8000");

    protected final HttpProtocolBuilder httpProtocol = http
            .baseUrl(baseUrl)
            .acceptHeader("text/html,application/json")
            .acceptLanguageHeader("fr-FR,fr;q=0.9")
            .userAgentHeader("Gatling/Biketory");

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
                                .disableFollowRedirect()
                                .header("Referer", baseUrl + "/register/")
                                .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                                .formParam("email", "#{email}")
                                .formParam("password1", "#{password}")
                                .formParam("password2", "#{password}")
                                .check(status().find().in(200,302))
                );
    }

    protected ChainBuilder login() {
        return fetchCsrf("GET /accounts/login/", "/accounts/login/")
                .pause(1, 2)
                .exec(
                        http("POST /accounts/login/")
                                .post("/accounts/login/")
                                .disableFollowRedirect()
                                .header("Referer", baseUrl + "/accounts/login/")
                                .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                                .formParam("login", "#{email}")
                                .formParam("password", "#{password}")
                                .check(status().find().in(200,302))
                                .check(header("Location").is("/dashboard/"))
                );
    }

    protected ChainBuilder uploadGpx() {
        return fetchCsrf("GET /upload/", "/upload/")
                .pause(1, 2)
                .exec(
                        http("POST /upload/")
                                .post("/upload/")
                                .disableFollowRedirect()
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

    protected static ScenarioBuilder statsApiScenario() {
        return scenario("API Stats")
                .exec(http("API stats monthly").get("/api/stats/monthly/")
                        .check(status().is(200))
                        .check(jsonPath("$.labels").exists())
                        .check(jsonPath("$.datasets").exists()))
                .pause(1, 2)
                .exec(http("API stats traces").get("/api/stats/traces/")
                        .check(status().is(200))
                        .check(jsonPath("$.labels").exists())
                        .check(jsonPath("$.datasets").exists()));
    }

    protected static ScenarioBuilder publicBrowsingScenario() {
        return scenario("Navigation publique")
                .exec(http("Landing page").get("/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("API hexagons").get("/api/hexagons/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("API hexagons bbox").get("/api/hexagons/?bbox=-2,46,4,49").check(status().is(200)))
                .pause(1, 3)
                .exec(http("À propos").get("/about/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Mentions légales").get("/legal/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Stats mensuelles").get("/stats/monthly/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Stats traces").get("/stats/traces/").check(status().is(200)))
                .pause(1, 3)
                .exec(http("Stats badges").get("/stats/badges/").check(status().is(200)));
    }

    protected ScenarioBuilder authenticatedBrowsingScenario(
            String username, String password) {
        return scenario("Navigation authentifiée")
                .exec(session -> session
                        .set("email", username + "@test.biketory.local")
                        .set("password", password))
                .exec(register())
                .pause(1, 2)
                .exec(login())
                .pause(1, 3)
                .exec(http("Leaderboard").get("/leaderboard/")
                        .check(status().is(200)))
                .pause(1, 3)
                .exec(http("Zone leaders").get("/leaderboard/zones/")
                        .check(status().is(200)))
                .pause(1, 3)
                .exec(http("Dashboard").get("/dashboard/")
                        .check(status().is(200)))
                .pause(1, 3)
                .exec(http("Friends").get("/friends/")
                        .check(status().is(200)))
                .pause(1, 3)
                .exec(http("Traces list").get("/traces/")
                        .check(status().is(200)));
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
                )
                .exec(session -> {
                    // Extract UUID from redirect URL: /traces/<uuid>/
                    String url = session.getString("traceUrl");
                    String uuid = url.replaceAll(".*/traces/([0-9a-f-]+)/.*", "$1")
                                      .replaceAll(".*/traces/([0-9a-f-]+)/?$", "$1");
                    return session.set("traceUuid", uuid);
                })
                .exec(
                        http("GET trace status")
                                .get("/api/traces/#{traceUuid}/status/")
                                .check(status().is(200))
                                .check(jsonPath("$.status").exists().saveAs("traceStatus"))
                );
    }

    protected ScenarioBuilder verifyStatsScenario() {
        return scenario("Verify stats")
                .exec(
                        http("GET /stats/monthly/")
                                .get("/stats/monthly/")
                                .check(status().is(200))
                )
                .pause(1, 2)
                .exec(
                        http("GET /stats/traces/")
                                .get("/stats/traces/")
                                .check(status().is(200))
                )
                .pause(1, 2)
                .exec(
                        http("GET /stats/badges/")
                                .get("/stats/badges/")
                                .check(status().is(200))
                );
    }

    protected ScenarioBuilder verifyStatsApiScenario() {
        return scenario("Verify Stats API")
                .exec(
                        http("Trigger compute_stats")
                                .get("/api/compute-stats/?granularity=month")
                                .check(status().is(200))
                                .check(jsonPath("$.status").is("ok"))
                )
                .pause(1, 2)
                .exec(
                        http("API stats monthly")
                                .get("/api/stats/monthly/")
                                .check(status().is(200))
                                .check(jsonPath("$.labels").exists())
                                .check(jsonPath("$.datasets").exists())
                                .check(jsonPath("$.datasets[*].label").count().gte(1))
                                .check(jsonPath("$.datasets[0].data").exists())
                )
                .pause(1, 2)
                .exec(
                        http("API stats traces")
                                .get("/api/stats/traces/")
                                .check(status().is(200))
                                .check(jsonPath("$.labels").exists())
                                .check(jsonPath("$.datasets").exists())
                                .check(jsonPath("$.datasets[0].label").is("Traces"))
                                .check(jsonPath("$.datasets[0].data").exists())
                );
    }

    /**
     * Sum all integer values found in "data" arrays within the JSON.
     * Works for both chart page JSON and API JSON structures.
     */
    protected static int sumAllDataValues(String json) {
        int total = 0;
        int searchFrom = 0;
        while (true) {
            int dataIdx = json.indexOf("\"data\"", searchFrom);
            if (dataIdx == -1) break;
            int arrayStart = json.indexOf("[", dataIdx);
            if (arrayStart == -1) break;
            int arrayEnd = json.indexOf("]", arrayStart);
            if (arrayEnd == -1) break;
            String[] values = json.substring(arrayStart + 1, arrayEnd).split(",");
            for (String v : values) {
                String trimmed = v.trim();
                if (!trimmed.isEmpty()) {
                    total += Integer.parseInt(trimmed);
                }
            }
            searchFrom = arrayEnd + 1;
        }
        return total;
    }

    /**
     * Sum all integer values from "data" arrays in an API stats JSON response.
     * JSON structure: {"labels":[...], "datasets":[{"label":"x","data":[...]}, ...]}
     */
    protected static int sumAllApiDataValues(String json) {
        return sumAllDataValues(json);
    }

    // -- Referral feeders & scenario ----------------------------------------------

    private static final String REF_PWD = "P@ss_ref_test!";

    protected static Iterator<Map<String, Object>> referralFeeder() {
        return List.<Map<String, Object>>of(
                Map.of("email", "test1@test.biketory.local", "password", REF_PWD, "refereeEmail", "test5@test.biketory.local"),
                Map.of("email", "test2@test.biketory.local", "password", REF_PWD, "refereeEmail", "test6@test.biketory.local"),
                Map.of("email", "test3@test.biketory.local", "password", REF_PWD, "refereeEmail", "test7@test.biketory.local"),
                Map.of("email", "test4@test.biketory.local", "password", REF_PWD, "refereeEmail", "test8@test.biketory.local")
        ).iterator();
    }

    protected static Iterator<Map<String, Object>> refereeFeeder() {
        return List.<Map<String, Object>>of(
                Map.of("email", "test5@test.biketory.local", "password", REF_PWD),
                Map.of("email", "test6@test.biketory.local", "password", REF_PWD),
                Map.of("email", "test7@test.biketory.local", "password", REF_PWD),
                Map.of("email", "test8@test.biketory.local", "password", REF_PWD)
        ).iterator();
    }

    protected ScenarioBuilder referralSponsorPhase() {
        return scenario("Referral — sponsors")
                .feed(referralFeeder())
                .exec(register())
                .pause(1, 2)
                .exec(login())
                .pause(1, 2)
                .exec(fetchCsrf("GET /referrals/", "/referrals/"))
                .exec(
                        http("POST /referrals/")
                                .post("/referrals/")
                                .disableFollowRedirect()
                                .header("Referer", baseUrl + "/referrals/")
                                .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                                .formParam("email", "#{refereeEmail}")
                                .check(status().is(302))
                )
                .pause(1, 2)
                .exec(
                        http("GET /referrals/ (extract token)")
                                .get("/referrals/")
                                .check(status().is(200))
                                .check(css("tr[data-token]", "data-token").saveAs("refToken"))
                )
                .exec(session -> {
                    String refereeEmail = session.getString("refereeEmail");
                    String refToken = session.getString("refToken");
                    referralTokens.put(refereeEmail, refToken);
                    return session;
                });
    }

    protected ScenarioBuilder referralRefereePhase() {
        return scenario("Referral — referees")
                .feed(refereeFeeder())
                .exec(session -> {
                    String email = session.getString("email");
                    String token = referralTokens.get(email);
                    return session.set("refToken", token);
                })
                .exec(
                        http("GET /register/?ref=token")
                                .get("/register/")
                                .queryParam("ref", "#{refToken}")
                                .check(status().is(200))
                                .check(css("input[name='csrfmiddlewaretoken']", "value")
                                        .saveAs("csrfToken"))
                )
                .pause(1, 2)
                .exec(
                        http("POST /register/ (referee)")
                                .post("/register/")
                                .disableFollowRedirect()
                                .header("Referer", baseUrl + "/register/")
                                .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                                .formParam("email", "#{email}")
                                .formParam("password1", "#{password}")
                                .formParam("password2", "#{password}")
                                .formParam("ref", "#{refToken}")
                                .check(status().find().in(200, 302))
                );
    }

    protected ScenarioBuilder referralVerifyPhase() {
        return scenario("Referral — verify")
                .feed(referralFeeder())
                .exec(login())
                .pause(1, 2)
                .exec(
                        http("GET /referrals/ (verify accepted)")
                                .get("/referrals/")
                                .check(status().is(200))
                                .check(css("span.badge-accepted").exists())
                );
    }
}
