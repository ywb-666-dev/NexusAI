package org.ibo.nexusjava.modules.approval.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.ibo.nexusjava.common.BusinessException;
import org.ibo.nexusjava.common.ErrorCode;
import org.ibo.nexusjava.interceptor.UserContext;
import org.ibo.nexusjava.modules.approval.dto.ApprovalTicketDTO;
import org.ibo.nexusjava.modules.approval.entity.ApprovalTicket;
import org.ibo.nexusjava.modules.approval.mapper.ApprovalTicketMapper;
import org.ibo.nexusjava.modules.approval.service.ApprovalTicketService;
import org.ibo.nexusjava.modules.approval.vo.ApprovalTicketVO;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ApprovalTicketServiceImpl extends ServiceImpl<ApprovalTicketMapper, ApprovalTicket> implements ApprovalTicketService {

    @org.springframework.beans.factory.annotation.Autowired private org.ibo.nexusjava.common.JwtUtil jwtUtil;
    private void requireAdmin() {
        if (!"admin".equals(UserContext.getRole())) throw new BusinessException(ErrorCode.PARAM_ERROR, "需要管理员权限");
    }
    private void resume(ApprovalTicket ticket, boolean approved) {
        try {
            var client = java.net.http.HttpClient.newHttpClient();
            var req = java.net.http.HttpRequest.newBuilder(java.net.URI.create("http://localhost:8000/api/python/agent/tasks/" + ticket.getTaskId() + "/resume?approved=" + approved))
                .header("Authorization", "Bearer " + jwtUtil.generateToken(UserContext.getUserId(), UserContext.getUsername(), UserContext.getRole()))
                .timeout(java.time.Duration.ofSeconds(15)).POST(java.net.http.HttpRequest.BodyPublishers.noBody()).build();
            var response = client.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) throw new IllegalStateException();
        } catch (Exception e) { throw new BusinessException(ErrorCode.SYSTEM_ERROR, "工单已处理，但任务恢复失败，请在任务中心重试恢复"); }
    }
    private ApprovalTicketVO convertToVO(ApprovalTicket ticket) {
        ApprovalTicketVO vo = new ApprovalTicketVO();
        vo.setId(ticket.getId());
        vo.setTaskId(ticket.getTaskId());
        vo.setUserId(ticket.getUserId());
        vo.setActionType(ticket.getActionType());
        vo.setRiskLevel(ticket.getRiskLevel());
        vo.setContext(ticket.getContext());
        vo.setStatus(ticket.getStatus());
        vo.setApprovedBy(ticket.getApprovedBy());
        vo.setApprovedAt(ticket.getApprovedAt());
        vo.setComment(ticket.getComment());
        vo.setCreatedAt(ticket.getCreatedAt());
        return vo;
    }

    @Override
    public IPage<ApprovalTicketVO> listPending(Long current, Long size) {
        requireAdmin();
        LambdaQueryWrapper<ApprovalTicket> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApprovalTicket::getStatus, 0);
        wrapper.orderByDesc(ApprovalTicket::getCreatedAt);

        Page<ApprovalTicket> page = new Page<>(current != null ? current : 1, size != null ? size : 10);
        page(page, wrapper);

        List<ApprovalTicketVO> records = page.getRecords().stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());

        Page<ApprovalTicketVO> resultPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        resultPage.setRecords(records);
        return resultPage;
    }

    @Override
    public ApprovalTicketVO getById(Long id) {
        requireAdmin();
        ApprovalTicket ticket = super.getById(id);
        if (ticket == null) {
            throw new BusinessException(ErrorCode.APPROVAL_TICKET_NOT_FOUND);
        }
        return convertToVO(ticket);
    }

    @Override
    public void approve(Long id, ApprovalTicketDTO dto) {
        requireAdmin();
        ApprovalTicket ticket = super.getById(id);
        if (ticket == null) {
            throw new BusinessException(ErrorCode.APPROVAL_TICKET_NOT_FOUND);
        }
        if (ticket.getStatus() != 0) {
            throw new BusinessException(ErrorCode.APPROVAL_ALREADY_PROCESSED);
        }
        Long approverId = UserContext.getUserId();
        ticket.setStatus(1);
        ticket.setApprovedBy(approverId);
        ticket.setComment(dto.getComment());
        ticket.setApprovedAt(LocalDateTime.now());
        boolean changed = lambdaUpdate().eq(ApprovalTicket::getId, id).eq(ApprovalTicket::getStatus, 0)
            .set(ApprovalTicket::getStatus, ticket.getStatus()).set(ApprovalTicket::getApprovedBy, approverId)
            .set(ApprovalTicket::getComment, dto.getComment()).set(ApprovalTicket::getApprovedAt, ticket.getApprovedAt()).update();
        if (!changed) throw new BusinessException(ErrorCode.APPROVAL_ALREADY_PROCESSED);
        resume(ticket, ticket.getStatus() == 1);
    }

    @Override
    public void reject(Long id, ApprovalTicketDTO dto) {
        requireAdmin();
        ApprovalTicket ticket = super.getById(id);
        if (ticket == null) {
            throw new BusinessException(ErrorCode.APPROVAL_TICKET_NOT_FOUND);
        }
        if (ticket.getStatus() != 0) {
            throw new BusinessException(ErrorCode.APPROVAL_ALREADY_PROCESSED);
        }
        Long approverId = UserContext.getUserId();
        ticket.setStatus(2);
        ticket.setApprovedBy(approverId);
        ticket.setComment(dto.getComment());
        ticket.setApprovedAt(LocalDateTime.now());
        boolean changed = lambdaUpdate().eq(ApprovalTicket::getId, id).eq(ApprovalTicket::getStatus, 0)
            .set(ApprovalTicket::getStatus, ticket.getStatus()).set(ApprovalTicket::getApprovedBy, approverId)
            .set(ApprovalTicket::getComment, dto.getComment()).set(ApprovalTicket::getApprovedAt, ticket.getApprovedAt()).update();
        if (!changed) throw new BusinessException(ErrorCode.APPROVAL_ALREADY_PROCESSED);
        resume(ticket, ticket.getStatus() == 1);
    }
}
