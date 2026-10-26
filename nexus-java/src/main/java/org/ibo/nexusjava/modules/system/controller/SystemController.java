package org.ibo.nexusjava.modules.system.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.approval.entity.ApprovalTicket;
import org.ibo.nexusjava.modules.approval.mapper.ApprovalTicketMapper;
import org.ibo.nexusjava.modules.content.entity.Content;
import org.ibo.nexusjava.modules.content.mapper.ContentMapper;
import org.ibo.nexusjava.modules.subscription.entity.Subscription;
import org.ibo.nexusjava.modules.subscription.mapper.SubscriptionMapper;
import org.ibo.nexusjava.modules.system.vo.ChartsVO;
import org.ibo.nexusjava.modules.system.vo.SystemMetricsVO;
import org.ibo.nexusjava.modules.user.entity.User;
import org.ibo.nexusjava.modules.user.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import org.springframework.data.redis.core.StringRedisTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import java.util.concurrent.TimeUnit;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/java/system")
public class SystemController {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private UserMapper userMapper;
    @Autowired
    private SubscriptionMapper subscriptionMapper;
    @Autowired
    private ContentMapper contentMapper;
    @Autowired
    private ApprovalTicketMapper approvalTicketMapper;

    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("ok");
    }

    @GetMapping("/metrics")
    public Result<SystemMetricsVO> metrics() {
        SystemMetricsVO vo = new SystemMetricsVO();
        vo.setTotalUsers("admin".equals(org.ibo.nexusjava.interceptor.UserContext.getRole()) ? userMapper.selectCount(null) : 1L);
        var ids = subscriptionMapper.selectList(new LambdaQueryWrapper<Subscription>().eq(Subscription::getUserId, org.ibo.nexusjava.interceptor.UserContext.getUserId())).stream().map(Subscription::getId).toList();
        vo.setTotalSubscriptions(subscriptionMapper.selectCount(new LambdaQueryWrapper<Subscription>().eq(Subscription::getUserId, org.ibo.nexusjava.interceptor.UserContext.getUserId()).ne(Subscription::getStatus, -1)));
        vo.setTotalContents(ids.isEmpty() ? 0L : contentMapper.selectCount(new LambdaQueryWrapper<Content>().in(Content::getSubscriptionId, ids).eq(Content::getStatus, 1)));

        LambdaQueryWrapper<ApprovalTicket> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApprovalTicket::getStatus, 0);
        if (!"admin".equals(org.ibo.nexusjava.interceptor.UserContext.getRole())) wrapper.eq(ApprovalTicket::getUserId, org.ibo.nexusjava.interceptor.UserContext.getUserId());
        vo.setPendingApprovals(approvalTicketMapper.selectCount(wrapper));

        Result<SystemMetricsVO> result = Result.success(vo);
        return result;
    }

    @GetMapping("/charts")
    public Result<ChartsVO> charts() {
        var ids = subscriptionMapper.selectList(new LambdaQueryWrapper<Subscription>().eq(Subscription::getUserId, org.ibo.nexusjava.interceptor.UserContext.getUserId())).stream().map(Subscription::getId).toList();
        List<Content> allContent = ids.isEmpty() ? List.of() : contentMapper.selectList(new LambdaQueryWrapper<Content>().in(Content::getSubscriptionId, ids).eq(Content::getStatus, 1));

        // 平台分布
        Map<String, Long> platformCount = allContent.stream()
                .collect(Collectors.groupingBy(
                        c -> c.getSourcePlatform() != null ? c.getSourcePlatform() : "未知",
                        Collectors.counting()
                ));
        List<ChartsVO.PlatformDist> platformDist = platformCount.entrySet().stream()
                .map(e -> {
                    ChartsVO.PlatformDist pd = new ChartsVO.PlatformDist();
                    pd.setPlatform(e.getKey());
                    pd.setCount(e.getValue());
                    return pd;
                })
                .collect(Collectors.toList());

        // 24小时趋势
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime since = now.minusHours(23);
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("MM-dd HH:mm");

        Map<String, Long> hourCount = allContent.stream()
                .filter(c -> c.getFetchedAt() != null && c.getFetchedAt().isAfter(since))
                .collect(Collectors.groupingBy(
                        c -> c.getFetchedAt().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH")) + ":00",
                        Collectors.counting()
                ));

        List<ChartsVO.HourlyTrend> hourlyTrend = hourCount.entrySet().stream()
                .map(e -> {
                    ChartsVO.HourlyTrend ht = new ChartsVO.HourlyTrend();
                    ht.setHour(e.getKey());
                    ht.setCount(e.getValue());
                    return ht;
                })
                .sorted((a, b) -> a.getHour().compareTo(b.getHour()))
                .collect(Collectors.toList());

        ChartsVO vo = new ChartsVO();
        vo.setPlatformDistribution(platformDist);
        vo.setHourlyTrend(hourlyTrend);
        return Result.success(vo);
    }
}
