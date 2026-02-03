"""
Patch/Routing API endpoints.

Manages audio routing between TF-Rack, Dante devices, and channels.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.patch import Patch, PatchType

router = APIRouter()


# ========== Pydantic Models ==========

class PatchCreate(BaseModel):
    patch_type: PatchType
    source_device: str
    source_port: int = Field(ge=1)
    source_channel_name: Optional[str] = None
    dest_device: str
    dest_port: int = Field(ge=1)
    dest_channel_name: Optional[str] = None
    channel_id: Optional[int] = None


class PatchResponse(BaseModel):
    id: int
    patch_type: PatchType
    source_device: str
    source_port: int
    source_channel_name: Optional[str]
    dest_device: str
    dest_port: int
    dest_channel_name: Optional[str]
    channel_id: Optional[int]
    dante_flow_id: Optional[str]

    class Config:
        from_attributes = True


class DanteSubscription(BaseModel):
    """Create a Dante audio subscription."""
    receiver_device: str
    receiver_channel: int = Field(ge=1)
    transmitter_device: str
    transmitter_channel: int = Field(ge=1)


class QuickPatch(BaseModel):
    """Quick patch for common routing scenarios."""
    input_number: int = Field(ge=1, le=32, description="TF-Rack input channel")
    source_type: str = Field(description="analog, dante_tio, or dante_other")
    source_device: Optional[str] = None  # For Dante sources
    source_port: int = Field(ge=1, description="Port number on source device")


# ========== API Endpoints ==========

@router.get("/", response_model=List[PatchResponse])
async def get_patches(
    patch_type: Optional[PatchType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all patches, optionally filtered by type."""
    query = select(Patch)
    if patch_type:
        query = query.where(Patch.patch_type == patch_type)

    result = await db.execute(query)
    patches = result.scalars().all()
    return patches


@router.get("/matrix")
async def get_patch_matrix(db: AsyncSession = Depends(get_db)):
    """
    Get the full patch matrix showing all current routing.

    Returns a matrix view of sources -> destinations.
    """
    result = await db.execute(select(Patch))
    patches = result.scalars().all()

    # Build matrix representation
    matrix = {
        "inputs": {},  # TF-Rack input patches
        "outputs": {},  # TF-Rack output patches (to Dante)
        "dante": []  # Other Dante patches
    }

    for patch in patches:
        if patch.patch_type == PatchType.ANALOG_TO_CHANNEL:
            matrix["inputs"][patch.dest_port] = {
                "type": "analog",
                "source": patch.source_port
            }
        elif patch.patch_type == PatchType.DANTE_TO_CHANNEL:
            matrix["inputs"][patch.dest_port] = {
                "type": "dante",
                "source_device": patch.source_device,
                "source_port": patch.source_port
            }
        elif patch.patch_type in [PatchType.CHANNEL_TO_DANTE, PatchType.AUX_TO_DANTE]:
            matrix["outputs"][patch.source_port] = {
                "dest_device": patch.dest_device,
                "dest_port": patch.dest_port
            }
        else:
            matrix["dante"].append({
                "source": f"{patch.source_device}:{patch.source_port}",
                "dest": f"{patch.dest_device}:{patch.dest_port}"
            })

    return matrix


@router.get("/{patch_id}", response_model=PatchResponse)
async def get_patch(patch_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific patch by ID."""
    result = await db.execute(select(Patch).where(Patch.id == patch_id))
    patch = result.scalar_one_or_none()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post("/", response_model=PatchResponse)
async def create_patch(
    patch: PatchCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new audio patch/route."""
    db_patch = Patch(**patch.model_dump())

    # If this is a Dante patch, create the subscription
    if patch.patch_type in [PatchType.DANTE_TO_CHANNEL, PatchType.CHANNEL_TO_DANTE,
                            PatchType.AUX_TO_DANTE]:
        if hasattr(request.app.state, 'dante'):
            # This would call the Dante controller to create the route
            pass

    db.add(db_patch)
    await db.commit()
    await db.refresh(db_patch)
    return db_patch


@router.delete("/{patch_id}")
async def delete_patch(
    patch_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete a patch."""
    result = await db.execute(select(Patch).where(Patch.id == patch_id))
    patch = result.scalar_one_or_none()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    # If Dante patch, remove the subscription
    if patch.dante_flow_id and hasattr(request.app.state, 'dante'):
        pass

    await db.delete(patch)
    await db.commit()
    return {"status": "ok", "deleted": patch_id}


@router.post("/dante/subscribe")
async def create_dante_subscription(
    sub: DanteSubscription,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a Dante audio subscription (route audio from transmitter to receiver)."""
    # Create patch record
    patch = Patch(
        patch_type=PatchType.DANTE_TO_CHANNEL,
        source_device=sub.transmitter_device,
        source_port=sub.transmitter_channel,
        dest_device=sub.receiver_device,
        dest_port=sub.receiver_channel
    )

    # Actually create the Dante subscription
    # TODO: Implement Dante Controller API integration
    # if hasattr(request.app.state, 'dante'):
    #     dante = request.app.state.dante
    #     dante.create_subscription(sub.transmitter_device, sub.transmitter_channel,
    #                               sub.receiver_device, sub.receiver_channel)

    db.add(patch)
    await db.commit()
    await db.refresh(patch)

    return {
        "status": "ok",
        "patch_id": patch.id,
        "route": f"{sub.transmitter_device}:{sub.transmitter_channel} -> {sub.receiver_device}:{sub.receiver_channel}"
    }


@router.delete("/dante/unsubscribe")
async def remove_dante_subscription(
    receiver_device: str,
    receiver_channel: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Remove a Dante audio subscription."""
    # Find and delete the patch
    result = await db.execute(
        select(Patch).where(
            Patch.dest_device == receiver_device,
            Patch.dest_port == receiver_channel,
            Patch.patch_type == PatchType.DANTE_TO_CHANNEL
        )
    )
    patch = result.scalar_one_or_none()

    if patch:
        await db.delete(patch)
        await db.commit()

    return {"status": "ok"}


@router.post("/quick-patch")
async def quick_patch_input(
    qp: QuickPatch,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Quick patch helper for common routing scenarios.

    Patches an input to a TF-Rack channel from either:
    - Analog input on TF-Rack
    - Dante TIO input
    - Other Dante device
    """
    if qp.source_type == "analog":
        # Direct analog patch (internal to TF-Rack)
        patch = Patch(
            patch_type=PatchType.ANALOG_TO_CHANNEL,
            source_device="TF-RACK",
            source_port=qp.source_port,
            dest_device="TF-RACK",
            dest_port=qp.input_number
        )
    elif qp.source_type == "dante_tio":
        # Dante from TIO stage box
        patch = Patch(
            patch_type=PatchType.DANTE_TO_CHANNEL,
            source_device=qp.source_device or "TIO-1608-D",
            source_port=qp.source_port,
            dest_device="TF-RACK",
            dest_port=qp.input_number
        )
    elif qp.source_type == "dante_other":
        # Dante from other device
        if not qp.source_device:
            raise HTTPException(status_code=400, detail="source_device required for dante_other")
        patch = Patch(
            patch_type=PatchType.DANTE_TO_CHANNEL,
            source_device=qp.source_device,
            source_port=qp.source_port,
            dest_device="TF-RACK",
            dest_port=qp.input_number
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    db.add(patch)
    await db.commit()
    await db.refresh(patch)

    return {
        "status": "ok",
        "patch_id": patch.id,
        "input": qp.input_number,
        "source": f"{patch.source_device}:{patch.source_port}"
    }


@router.post("/auto-patch-tio")
async def auto_patch_tio(
    tio_name: str,
    start_channel: int = 1,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-patch a TIO-1608-D to TF-Rack channels.

    Maps TIO inputs 1-16 to TF-Rack channels starting at start_channel.
    """
    patches = []

    for i in range(16):  # TIO-1608-D has 16 inputs
        tf_channel = start_channel + i
        if tf_channel > 32:  # TF-Rack has 32 inputs
            break

        patch = Patch(
            patch_type=PatchType.DANTE_TO_CHANNEL,
            source_device=tio_name,
            source_port=i + 1,
            dest_device="TF-RACK",
            dest_port=tf_channel
        )
        db.add(patch)
        patches.append({
            "tio_input": i + 1,
            "tf_channel": tf_channel
        })

    await db.commit()

    return {
        "status": "ok",
        "tio": tio_name,
        "patches": patches
    }
