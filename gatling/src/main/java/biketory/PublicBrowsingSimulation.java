package biketory;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class PublicBrowsingSimulation extends Simulation {

    private final String baseUrl = System.getProperty("baseUrl", "http://localhost:8000");

    private final HttpProtocolBuilder httpProtocol = http
            .baseUrl(baseUrl)
            .acceptHeader("text/html,application/json")
            .acceptLanguageHeader("fr-FR,fr;q=0.9")
            .userAgentHeader("Gatling/Biketory");

    private final ScenarioBuilder publicBrowsing = scenario("Navigation publique")
            .exec(
                    http("Landing page")
                            .get("/")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("API hexagons")
                            .get("/api/hexagons/")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("API hexagons bbox")
                            .get("/api/hexagons/?bbox=-2,46,4,49")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("Mentions légales")
                            .get("/legal/")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("Stats utilisateur")
                            .get("/stats/")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("Stats mensuelles")
                            .get("/stats/monthly/")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("Répartition")
                            .get("/stats/pie/")
                            .check(status().is(200))
            )
            .pause(1, 3)
            .exec(
                    http("Badges")
                            .get("/stats/badges/")
                            .check(status().is(200))
            );

    {
        setUp(
                publicBrowsing.injectOpen(
                        atOnceUsers(1)
                )
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(2000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
