package org.ibo.nexusjava.modules.approval.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.approval.dto.ApprovalTicketDTO;
import org.ibo.nexusjava.modules.approval.service.ApprovalTicketService;
import org.ibo.nexusjava.modules.approval.vo.ApprovalTicketVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/java/approvals")
public class ApprovalTicketController {

    @Autowired
    private ApprovalTicketService approvalTicketService;

    @GetMapping("/pending")
    public Result<IPage<ApprovalTicketVO>> listPending(
            @RequestParam(required = false, defaultValue = "1") Long current,
            @RequestParam(required = false, defaultValue = "10") Long size) {
        return Result.success(approvalTicketService.listPending(current, size));
    }

    @GetMapping("/{id}")
    public Result<ApprovalTicketVO> getById(@PathVariable Long id) {
        return Result.success(approvalTicketService.getById(id));
    }

    @PostMapping("/{id}/approve")
    public Result<Void> approve(@PathVariable Long id, @RequestBody ApprovalTicketDTO dto) {
        approvalTicketService.approve(id, dto);
        return Result.success();
    }

    @PostMapping("/{id}/reject")
    public Result<Void> reject(@PathVariable Long id, @RequestBody ApprovalTicketDTO dto) {
        approvalTicketService.reject(id, dto);
        return Result.success();
    }
}
