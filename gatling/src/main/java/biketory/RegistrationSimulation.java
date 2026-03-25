package biketory;

import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Stream;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class RegistrationSimulation extends Simulation {

    private final String baseUrl = System.getProperty("baseUrl", "http://localhost:8000");

    private static final Iterator<Map<String, Object>> usersFeeder =
            Stream.generate((Supplier<Map<String, Object>>) () -> {
                String uid = UUID.randomUUID().toString().substring(0, 8);
                return Map.of(
                        "username", "user_" + uid,
                        "email", "user_" + uid + "@test.biketory.local",
                        "password", "P@ss_" + uid + "!"
                );
            }).iterator();

    private final HttpProtocolBuilder httpProtocol = http
            .baseUrl(baseUrl)
            .acceptHeader("text/html,application/json")
            .acceptLanguageHeader("fr-FR,fr;q=0.9")
            .userAgentHeader("Gatling/Biketory")
            .disableFollowRedirect();

    private final ScenarioBuilder registration = scenario("Création de compte")
            .feed(usersFeeder)
            .exec(
                    http("GET /register/")
                            .get("/register/")
                            .check(status().is(200))
                            .check(css("input[name='csrfmiddlewaretoken']", "value")
                                    .saveAs("csrfToken"))
            )
            .pause(1, 3)
            .exec(
                    http("POST /register/")
                            .post("/register/")
                            .header("Referer", baseUrl + "/register/")
                            .formParam("csrfmiddlewaretoken", "#{csrfToken}")
                            .formParam("username", "#{username}")
                            .formParam("email", "#{email}")
                            .formParam("password1", "#{password}")
                            .formParam("password2", "#{password}")
                            .check(status().is(200))

            );

    {
        setUp(
                registration.injectOpen(
                        atOnceUsers(2)
                )
        )
                .protocols(httpProtocol)
                .assertions(
                        global().responseTime().percentile(95.0).lt(2000),
                        global().successfulRequests().percent().gt(95.0)
                );
    }
}
