package org.ibo.nexusjava.common;

import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import io.jsonwebtoken.*;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * Token生成与解析
 *
 * @author: yi327
 * @date: 2026/5/27
 */
@Component
public class JwtUtil {
    @Value("${jwt.secret}")
    private String secret;
    @Value("${jwt.expiration}")

    private String expiration;//单位毫秒
    // 构造或初始化时，把 secret 转成 javax.crypto.SecretKey 缓存起来
    //避免每次调用都重新生成密钥对象
    private SecretKey key;

    /**
     * 初始化key
     */
    @PostConstruct
    public void init() {
        byte[] bytes=secret.getBytes(StandardCharsets.UTF_8);
        if(bytes.length<32) {
            throw new IllegalArgumentException("secret长度不足32位");
        }
        this.key= Keys.hmacShaKeyFor(bytes);
    }

    /**
     * 生成token
     * @param userId 用户ID(用户唯一标识)
     * @param username 用户名
     * @param role 用户角色（admin/user），用来管理权限
     * @return 返回token
     */
    public String generateToken(Long userId,String username,String role) {
        Date now=new Date();//标记 Token 的签发时间
        Date exp=new Date(now.getTime() + expiration);//计算 Token 过期时间
        return Jwts.builder()//JJWT 库提供的固定入口，用于链式创建 JWT 对象
                .subject(String.valueOf(userId))
                .claim("username",username)
                .claim("role",role)
                .issuedAt(now)
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    /**
     * 解析token
     * @param token JwtToken
     * @return  Claims 对象 {sub=1, username=test, role=user, iat=..., exp=...}
     */
    public Claims parseToken(String token) {
        return Jwts.parser()//拿到builder
                .verifyWith(key)//配置验签密钥
                .build()//生成解析器
                .parseSignedClaims(token)//解码 + 验签 + 时间校验
                .getPayload();//提取payload数据
    }

    public Long getUserIDFromToken(String token) {
        return Long.valueOf(parseToken(token).getSubject());
    }
    public String getUsernameFromToken(String token) {
        return parseToken(token).get("username",String.class);
    }

}
