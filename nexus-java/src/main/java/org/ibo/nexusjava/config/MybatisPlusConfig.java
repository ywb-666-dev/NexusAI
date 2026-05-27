package org.ibo.nexusjava.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 注册MybatisPlus分页插件
 * @author: yi327
 * @date: 2026/5/27
 */

@Configuration
public class MybatisPlusConfig {
    /**
     * 步骤说明：
     * 1. 创建 MybatisPlusInterceptor（它是 MyBatis-Plus 的【插件总容器】）
     * 2. 往容器里加入【分页内拦截器 PaginationInnerInterceptor】
     *    必须显式指定 DbType.SQL_SERVER，否则分页 SQL 可能按 MySQL 语法生成 LIMIT，SQL Server 会报错
     * 3. 返回给 Spring 容器
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        // 添加分页插件，指定数据库类型为 SQL Server
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.SQL_SERVER));
        return interceptor;
    }
}
