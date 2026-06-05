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
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/java/system")
public class SystemController {

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
        vo.setTotalUsers(userMapper.selectCount(null));
        vo.setTotalSubscriptions(subscriptionMapper.selectCount(null));
        vo.setTotalContents(contentMapper.selectCount(null));

        LambdaQueryWrapper<ApprovalTicket> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApprovalTicket::getStatus, 0);
        vo.setPendingApprovals(approvalTicketMapper.selectCount(wrapper));

        return Result.success(vo);
    }

    @GetMapping("/charts")
    public Result<ChartsVO> charts() {
        List<Content> allContent = contentMapper.selectList(null);

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
