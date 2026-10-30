/*---------------------------------------------------------------------------*\
Class
    isannStore

Description
    Store of the (state, dt, GA18 result) pairs that ISANN collects while the
    flame runs, with a first deduplication level so that thousands of cells in
    the same burnt gas do not fill the file with the same point.

    Each candidate is given a key on a coarse grid of a few coordinates:
        T / dT,  sqrt(Z) / dZ,  log10(max(Y_k, Y_floor)) / dlogY for a list of
        key species,  log10(dt) / dlogDt
    (floors of each). Every grid box keeps at most `cap` pairs. When a box is
    full, a new candidate replaces a random kept one with probability
    cap / n (reservoir sampling, n = candidates the box has seen), so the box
    holds a uniform sample of everything that fell into it over the run,
    not only the first states of the start-up.

    The finer, full-space deduplication (radius of novelty in the OOD
    coordinates of the model) is done in Python by openfoam/isann/isann.py
    when the pairs of all ranks are merged.

    Plain C++, no OpenFOAM types: also compiled into the offline test
    (openfoam/isann/dedup_test.cpp) that measures the reduction on DI
    snapshots.

\*---------------------------------------------------------------------------*/

#ifndef isannStore_H
#define isannStore_H

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

struct isannRecord
{
    long id;            // rank * 2^52 + start step * 2^32 + candidate counter: unique over
                        //  the run and its restarts
    int step;           // flow time index
    double time;
    int reason;         // 0 DI phase, 1 OOD, 2 untrusted bin, 3 shadow check
    int version;        // ANN version active when the pair was taken (0 = none)
    double T0, p, dt, Z;
    std::vector<double> Y0;
    double T1;
    std::vector<double> Y1;
};


class isannStore
{
public:
    // Grid widths
    double wT = 25.0, wZ = 0.02, wLogY = 0.25, wLogDt = 0.1, yFloor = 1e-8;
    std::vector<int> keySpecies;   // model species indices used in the key
    int cap = 2;

    // Counters over the run
    long nCandidates = 0, nNewBoxes = 0, nReplaced = 0;

    explicit isannStore(int rank = 0, long startStep = 0, unsigned seed = 1)
    :
        rank_(rank), startStep_(startStep), rng_(seed + 7919u*rank + 104729u*unsigned(startStep))
    {}

    uint64_t key(double T, double Z, const double* Y, double dt) const
    {
        uint64_t h = 1469598103934665603ull;     // FNV-1a over the box indices
        auto mix = [&h](long v)
        {
            for (int b = 0; b < 8; b++)
            {
                h ^= uint64_t((v >> (8*b)) & 0xff);
                h *= 1099511628211ull;
            }
        };
        mix(long(std::floor(T/wT)));
        mix(long(std::floor(std::sqrt(std::max(Z, 0.0))/wZ)));
        for (int k : keySpecies)
        {
            mix(long(std::floor(std::log10(std::max(Y[k], yFloor))/wLogY)));
        }
        mix(long(std::floor(std::log10(std::max(dt, 1e-30))/wLogDt)));
        return h;
    }

    //- Offer a candidate; returns true if it was kept (new or replacing one)
    //  `make` fills the record only when it is kept (the copy costs more than the key)
    template<class Make>
    bool offer(uint64_t k, Make make)
    {
        nCandidates++;
        Box& b = boxes_[k];
        b.n++;
        if (b.n == 1) nNewBoxes++;
        int slot = -1;
        if (int(b.slots.size()) < cap)
        {
            slot = int(records_.size());
            records_.emplace_back();
            b.slots.push_back(slot);
        }
        else
        {
            std::uniform_int_distribution<long> u(0, b.n - 1);
            const long j = u(rng_);
            if (j >= cap) return false;
            slot = b.slots[j];
            nReplaced++;
        }
        isannRecord& r = records_[slot];
        make(r);
        r.id = (long(rank_) << 52) + (startStep_ << 32) + nCandidates;
        return true;
    }

    long nBoxes() const { return long(boxes_.size()); }
    long nStored() const { return long(records_.size()); }
    const std::vector<isannRecord>& records() const { return records_; }

    //- Write all kept pairs to path (through a temporary file and a rename,
    //  so a reader never sees half a file)
    bool write(const std::string& path, const std::vector<std::string>& names) const
    {
        const std::string tmp = path + ".tmp";
        FILE* f = std::fopen(tmp.c_str(), "w");
        if (!f) return false;
        std::fprintf(f, "id,step,time,reason,version,T0,p,dt,Z,T1");
        for (const auto& n : names) std::fprintf(f, ",Y0_%s", n.c_str());
        for (const auto& n : names) std::fprintf(f, ",Y1_%s", n.c_str());
        std::fprintf(f, "\n");
        for (const auto& r : records_)
        {
            std::fprintf(f, "%ld,%d,%.9g,%d,%d,%.10g,%.10g,%.6g,%.8g,%.10g",
                r.id, r.step, r.time, r.reason, r.version, r.T0, r.p, r.dt, r.Z, r.T1);
            for (double y : r.Y0) std::fprintf(f, ",%.10g", y);
            for (double y : r.Y1) std::fprintf(f, ",%.10g", y);
            std::fprintf(f, "\n");
        }
        std::fclose(f);
        return std::rename(tmp.c_str(), path.c_str()) == 0;
    }

private:
    struct Box { long n = 0; std::vector<int> slots; };
    int rank_;
    long startStep_;
    std::mt19937_64 rng_;
    std::unordered_map<uint64_t, Box> boxes_;
    std::vector<isannRecord> records_;
};

#endif
