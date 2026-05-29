package org.ibo.nexusjava.modules.system.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.approval.entity.ApprovalTicket;
import org.ibo.nexusjava.modules.approval.mapper.ApprovalTicketMapper;
import org.ibo.nexusjava.modules.content.entity.Content;
import org.ibo.nexusjava.modules.content.mapper.ContentMapper;
import org.ibo.nexusjava.modules.subscription.entity.Subscription;
import org.ibo.nexusjava.modules.subscription.mapper.SubscriptionMapper;
import org.ibo.nexusjava.modules.system.vo.SystemMetricsVO;
import org.ibo.nexusjava.modules.user.entity.User;
import org.ibo.nexusjava.modules.user.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

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
}
