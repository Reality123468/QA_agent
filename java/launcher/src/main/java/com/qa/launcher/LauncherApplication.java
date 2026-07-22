package com.qa.launcher;

import java.io.File;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class LauncherApplication {

    private static final String[] MODULES = {"auth", "document", "chat", "audit", "frontend"};
    private static final int[] PORTS = {8080, 8081, 8082, 8083, 5173};
    private static final int START_DELAY_MS = 4000;
    private static final int HEALTH_CHECK_TIMEOUT_S = 120;

    public static void main(String[] args) throws Exception {
        // Use working directory as java/ root (user should run from java/)
        File javaDir = new File(System.getProperty("user.dir"));
        // Verify we're in the right place
        if (!new File(javaDir, "pom.xml").exists()) {
            System.err.println("ERROR: Must run from java/ directory.");
            System.err.println("  cd E:/vs_code_coding/QA_agent/java");
            System.err.println("  mvn -pl launcher exec:java");
            System.exit(1);
        }

        // Create logs directory
        Path logsDir = Paths.get(javaDir.getAbsolutePath(), "logs");
        Files.createDirectories(logsDir);

        System.out.println();
        System.out.println("========================================");
        System.out.println("  QA Agent Launcher");
        System.out.println("  Java dir: " + javaDir.getAbsolutePath());
        System.out.println("  Logs dir: " + logsDir);
        System.out.println("========================================");
        System.out.println();

        List<Process> processes = new ArrayList<>();

        // Shutdown hook — kill all child processes on Ctrl+C
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\nStopping all modules...");
            for (int i = processes.size() - 1; i >= 0; i--) {
                Process p = processes.get(i);
                if (p.isAlive()) {
                    p.destroyForcibly();
                    try { Thread.sleep(500); } catch (InterruptedException ignored) {}
                }
                System.out.println("  [" + MODULES[i] + "] stopped");
            }
            System.out.println("All modules stopped.");
        }));

        // Resolve mvn executable with full path (ProcessBuilder needs it when PATH isn't inherited)
        String mvnCmd = resolveMaven(javaDir);

        // Start each module
        Map<String, File> logFiles = new LinkedHashMap<>();
        for (int i = 0; i < MODULES.length; i++) {
            String module = MODULES[i];
            int port = PORTS[i];

            System.out.printf("[%d/%d] Starting %s on port %d...%n", i + 1, MODULES.length, module, port);

            File logFile = logsDir.resolve(module + ".log").toFile();
            logFiles.put(module, logFile);

            ProcessBuilder pb;
            if (module.equals("frontend")) {
                String npmCmd = resolveNpm();
                pb = new ProcessBuilder(npmCmd, "run", "dev");
                pb.directory(new File(javaDir, "frontend"));
            } else {
                pb = new ProcessBuilder(
                        mvnCmd, "-pl", module, "spring-boot:run"
                );
                pb.directory(javaDir);
            }
            pb.redirectErrorStream(true);
            pb.redirectOutput(ProcessBuilder.Redirect.to(logFile));
            // Ensure Maven uses the correct Java home
            pb.environment().put("JAVA_HOME", System.getProperty("java.home"));

            try {
                Process p = pb.start();
                processes.add(p);
            } catch (IOException e) {
                System.err.printf("  ERROR: Failed to start %s: %s%n", module, e.getMessage());
                // Kill already-started processes
                for (Process prev : processes) {
                    prev.destroyForcibly();
                }
                System.exit(1);
            }

            // Wait between starts
            try { Thread.sleep(START_DELAY_MS); } catch (InterruptedException ignored) {}
        }

        System.out.println();
        System.out.println("Waiting for modules to be ready...");
        System.out.println();

        // Health check loop
        boolean allReady = waitForReady(PORTS, MODULES, HEALTH_CHECK_TIMEOUT_S);

        System.out.println();
        if (allReady) {
            System.out.println("All modules started successfully!");
        } else {
            System.out.println("Some modules may not be ready. Check logs/ for details.");
        }
        System.out.println();
        System.out.println("  Auth:     http://localhost:8080/api/auth/login");
        System.out.println("  Document: http://localhost:8081/api/documents");
        System.out.println("  Chat:     http://localhost:8082/api/chat/stream");
        System.out.println("  Audit:    http://localhost:8083/api/audit/logs");
        System.out.println("  Frontend: http://localhost:5173");
        System.out.println();
        System.out.println("Logs: " + logsDir);
        System.out.println("Press Ctrl+C to stop all modules.");
        System.out.println();

        // Block main thread so child processes keep running
        try { Thread.currentThread().join(); } catch (InterruptedException ignored) {}
    }

    private static boolean waitForReady(int[] ports, String[] modules, int timeoutSeconds) {
        long deadline = System.currentTimeMillis() + timeoutSeconds * 1000L;
        boolean[] ready = new boolean[ports.length];
        int readyCount = 0;

        while (readyCount < ports.length && System.currentTimeMillis() < deadline) {
            for (int i = 0; i < ports.length; i++) {
                if (!ready[i]) {
                    if (isPortReady(ports[i])) {
                        ready[i] = true;
                        readyCount++;
                        System.out.printf("  [%s] ✓ READY (port %d)%n", modules[i], ports[i]);
                    }
                }
            }
            if (readyCount < ports.length) {
                try { Thread.sleep(2000); } catch (InterruptedException ignored) {}
            }
        }

        // Report any that didn't start
        for (int i = 0; i < ports.length; i++) {
            if (!ready[i]) {
                System.out.printf("  [%s] ✗ TIMEOUT (port %d) - check logs/%s.log%n",
                        modules[i], ports[i], modules[i]);
            }
        }

        return readyCount == ports.length;
    }

    private static boolean isPortReady(int port) {
        try {
            String path = port == 5173 ? "/" : "/api/auth/login";
            URL url = new URL("http://localhost:" + port + path);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(2000);
            conn.setReadTimeout(2000);
            conn.setRequestMethod("GET");
            int code = conn.getResponseCode();
            conn.disconnect();
            // Any HTTP response means the port is listening
            return code > 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean isWindows() {
        return System.getProperty("os.name").toLowerCase().contains("win");
    }

    private static String resolveNpm() {
        String npmName = "npm" + (isWindows() ? ".cmd" : "");
        String pathEnv = System.getenv("PATH");
        if (pathEnv != null) {
            for (String dir : pathEnv.split(File.pathSeparator)) {
                File npm = new File(dir, npmName);
                if (npm.exists()) return npm.getAbsolutePath();
            }
        }
        return npmName; // fallback
    }

    private static String resolveMaven(File javaDir) {
        String winExt = isWindows() ? ".cmd" : "";

        // 1. Try mvnw in java/ first
        String mvnwName = "mvnw" + winExt;
        File mvnw = new File(javaDir, mvnwName);
        if (mvnw.exists()) return mvnw.getAbsolutePath();

        // 2. Try MAVEN_HOME/bin/mvn
        String mavenHome = System.getenv("MAVEN_HOME");
        if (mavenHome != null) {
            File mvn = new File(new File(mavenHome, "bin"), "mvn" + winExt);
            if (mvn.exists()) return mvn.getAbsolutePath();
        }

        // 3. Search PATH for mvn
        String pathEnv = System.getenv("PATH");
        if (pathEnv != null) {
            for (String dir : pathEnv.split(File.pathSeparator)) {
                File mvn = new File(new File(dir), "mvn" + winExt);
                if (mvn.exists()) return mvn.getAbsolutePath();
            }
        }

        // 4. Fallback
        return "mvn" + winExt;
    }
}
