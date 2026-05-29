package org.ibo.nexusjava;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("org.ibo.nexusjava.modules.*.mapper")
public class NexusJavaApplication {

    public static void main(String[] args) {
        SpringApplication.run(NexusJavaApplication.class, args);
    }

}
